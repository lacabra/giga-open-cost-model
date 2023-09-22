from copy import deepcopy

from giga.schemas.conf.models import FiberTechnologyCostConf
from giga.viz.notebooks.parameters.parameter_sheet import ParameterSheet


METERS_IN_KM = 1_000.0

FIBER_MODEL_PARAMETERS = [
    {
        "parameter_name": "annual_bandwidth_cost_per_mbps",
        "parameter_input_name": "Annual cost per Mbps (USD)",
        "parameter_interactive": {
            "parameter_type": "float_slider",
            "value": 1,
            "min": 0,
            "max": 1800,
            "step": 0.01,
            "show_default": True,
        },
    },
    {
        "parameter_name": "setup_cost",
        "parameter_input_name": "Setup Cost (USD)",
        "parameter_interactive": {
            "parameter_type": "int_slider",
            "value": 1_000,
            "min": 0,
            "max": 10000,
            "step": 1,
            "show_default": True,
        },
    },
    {
        "parameter_name": "cost_per_km",
        "parameter_input_name": "Cost Per km (USD)",
        "parameter_interactive": {
            "parameter_type": "int_slider",
            "value": 8_900,
            "min": 0,
            "max": 60000,
            "step": 1,
            "show_default": True,
        },
    },
    {
        "parameter_name": "opex_cost_per_km",
        "parameter_input_name": "Maintenance Cost per km (USD)",
        "parameter_interactive": {
            "parameter_type": "int_slider",
            "value": 100,
            "min": 0,
            "max": 1_000,
            "step": 10,
            "show_default": True,
        },
    },
    {
        "parameter_name": "maximum_connection_length",
        "parameter_input_name": "Maximum Connection Length (km)",
        "parameter_interactive": {
            "parameter_type": "int_slider",
            "value": 20,
            "min": 0,
            "max": 100,
            "step": 1,
            "show_default": True,
        },
    },
    {
        "parameter_name": "required_power",
        "parameter_input_name": "Annual Power Required (kWh)",
        "parameter_interactive": {
            "parameter_type": "int_slider",
            "value": 500,
            "min": 0,
            "max": 1_000,
            "step": 10,
            "show_default": True,
        },
    },
    {
        "parameter_name": "economies_of_scale",
        "parameter_input_name": "Economies of Scale",
        "parameter_interactive": {
            "parameter_type": "bool_checkbox",
            "value": True,
            "description": "ON",
        },
    },
    {
        "parameter_name": "schools_as_fiber_nodes",
        "parameter_input_name": "Schools as fiber nodes",
        "parameter_interactive": {
            "parameter_type": "bool_checkbox",
            "value": True,
            "description": "ON",
        },
    },
]


class FiberTechnologyParameterManager:
    def __init__(self, sheet_name="fiber", parameters=FIBER_MODEL_PARAMETERS):
        self.sheet_name = sheet_name
        self.parameters = {p["parameter_name"]: p for p in parameters}
        self.sheet = ParameterSheet(sheet_name, parameters)

    def update_parameters(self, config):
        if len(config) == 0:
            return
        self.sheet.update_parameter("setup_cost", config["capex"]["fixed_costs"])
        self.sheet.update_parameter("cost_per_km", config["capex"]["cost_per_km"])
        self.sheet.update_parameter(
            "economies_of_scale", config["capex"]["economies_of_scale"]
        )
        self.sheet.update_parameter(
            "schools_as_fiber_nodes", config["capex"]["schools_as_fiber_nodes"]
        )
        self.sheet.update_parameter("opex_cost_per_km", config["opex"]["cost_per_km"])
        self.sheet.update_parameter(
            "annual_bandwidth_cost_per_mbps",
            config["opex"]["annual_bandwidth_cost_per_mbps"],
        )
        self.sheet.update_parameter(
            "maximum_connection_length",
            config["constraints"]["maximum_connection_length"] #/ METERS_IN_KM,
        )
        self.sheet.update_parameter(
            "required_power", config["constraints"]["required_power"]
        )

    def input_parameters(self, show_defaults = True):
        return self.sheet.input_parameters(show_defaults)

    def get_parameter_from_sheet(self, parameter_name):
        return self.sheet.get_parameter_value(parameter_name)

    def freeze(self):
        self.sheet.freeze()

    def unfreeze(self):
        self.sheet.unfreeze()

    def get_model_parameters(self):
        setup_cost = float(self.get_parameter_from_sheet("setup_cost"))
        cost_per_km = float(self.get_parameter_from_sheet("cost_per_km"))
        annual_cost_per_mbps = float(
            self.get_parameter_from_sheet("annual_bandwidth_cost_per_mbps")
        )
        economies_of_scale = bool(
            float(self.get_parameter_from_sheet("economies_of_scale"))
        )
        schools_as_fiber_nodes = bool(
            float(self.get_parameter_from_sheet("schools_as_fiber_nodes"))
        )
        opex_per_km = float(self.get_parameter_from_sheet("opex_cost_per_km"))
        required_power = float(self.get_parameter_from_sheet("required_power"))
        maximum_connection_length = (
            float(self.get_parameter_from_sheet("maximum_connection_length"))# * 1_000.0
        )  # meters
        return FiberTechnologyCostConf(
            capex={
                "fixed_costs": setup_cost,
                "cost_per_km": cost_per_km,
                "economies_of_scale": economies_of_scale,
                "schools_as_fiber_nodes": schools_as_fiber_nodes,
            },
            opex={
                "cost_per_km": opex_per_km,
                "annual_bandwidth_cost_per_mbps": annual_cost_per_mbps,
            },
            constraints={
                "maximum_connection_length": maximum_connection_length,
                "required_power": required_power,
                "maximum_bandwithd": 2_000.0,
            },
        )
