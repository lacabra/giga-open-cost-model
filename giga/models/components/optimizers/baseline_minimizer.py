import numpy as np
import math
from typing import List

from giga.schemas.conf.models import CostMinimizerConf
from giga.schemas.output import OutputSpace
from giga.schemas.output import SchoolConnectionCosts


class BaselineMinimizer:
    """
    Implements the baseline minimizer which selects the cheapest feasible technology
    For each school independently, if costs are not feasible, the school is considered not connected
    """

    def __init__(self, config: CostMinimizerConf):
        self.config = config

    def single_school_minimum_cost(
        self, school_id: str, costs: List[SchoolConnectionCosts]
    ) -> SchoolConnectionCosts:
        """
        Finds the minimum costs for a single school

        :param school_id: the identifier of the school in question
        :param costs, a list of costs for each technology
        :return: the minimum costs for the school

        """
        feasible = any(list(map(lambda x: x.feasible, costs)))
        if not feasible:
            reasons = ",".join(
                list(map(lambda x: "" if x.reason is None else x.reason, costs))
            ).strip(",")
            return SchoolConnectionCosts(
                school_id=school_id,
                capex=math.nan,
                opex=math.nan,
                opex_provider=math.nan,
                opex_consumer=math.nan,
                technology="None",
                feasible=False,
                reason=reasons,
            )
        else:
            totals = [
                c.technology_connectivity_cost(self.config.years_opex) for c in costs
            ]
            idx = np.nanargmin(totals)
            return costs[idx]

    def run(self, output: OutputSpace) -> List[SchoolConnectionCosts]:
        """
        Runs the baseline minimizer which selects the cheapest feasible technology for the
        schools that have cost results in the output space
        :param output: the output space containing the costs for each school
        :return: a list of minimum costs for each school
        """
        minimum_costs = [
            self.single_school_minimum_cost(school_id, list(technology_costs.values()))
            for school_id, technology_costs in output.aggregated_costs.items()
        ]
        return minimum_costs
