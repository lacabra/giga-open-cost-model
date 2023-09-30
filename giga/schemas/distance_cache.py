import os
import math
from pydantic import BaseModel
from typing import List, Dict
import pandas as pd

try:
    import ujson as json
except ImportError:
    import json

from giga.schemas.geo import PairwiseDistance, UniqueCoordinate
from giga.data.store.stores import COUNTRY_DATA_STORE as data_store
from giga.models.nodes.graph.pairwise_distance_model import DEFAULT_DISTANCE_FN

def encode_coord(coord):
    # turn tuple to list
    coord["coordinate"] = list(coord["coordinate"])
    return json.dumps(coord)


def decode_coord(coord):
    return UniqueCoordinate(**json.loads(coord))


class SingleLookupDistanceCache(BaseModel):
    """Cache for existing distance data with one to one mapping"""

    lookup: Dict[str, PairwiseDistance]
    cache_type: str = "one-to-one"

    def get(self, key: str, default: None) -> PairwiseDistance:
        return self.lookup.get(key, default)

    def get_distance(self, key: str, default: float = math.inf) -> float:
        if not key in self.lookup:
            return default
        return self.lookup[key].distance

    @staticmethod
    def from_distances(distances):
        # turn a List[PairwieDistance] into Dict[id, PairwiseDistance]
        tmp = {}
        for p in distances:
            id_source, id_target = p.pair_ids
            if id_source == id_target:
                continue
            else:
                if id_source in tmp:
                    tmp[id_source].append((id_target, p))
                else:
                    tmp[id_source] = [(id_target, p)]
        # source -> closest
        lookup = {}
        for k, v in tmp.items():
            closest_id, closest_distance = min(v, key=lambda x: x[1].distance)
            lookup[k] = closest_distance
        return SingleLookupDistanceCache(lookup=lookup)

    @staticmethod
    def from_json(file):
        with data_store.open(file, "r") as f:
            d = json.load(f)
        return SingleLookupDistanceCache(**d)

    def to_json(self, file):
        with data_store.open(file, "w") as f:
            json.dump(self.dict(), f)

    def __len__(self):
        return len(self.lookup)


class MultiLookupDistanceCache(BaseModel):
    """Cache for existing distance data with one to many mapping"""

    lookup: Dict[str, List[PairwiseDistance]]
    n_neighbors: int
    cache_type: str = "one-to-many"

    @staticmethod
    def from_distances(distances, n_neighbors=10):
        tmp = {}
        for p in distances:
            id_source, id_target = p.pair_ids
            if id_source == id_target:
                continue
            else:
                # reverse ID ordering to preserve edge direction
                revids = p.copy()
                revids.pair_ids = tuple(reversed(revids.pair_ids))
                revids.coordinate1, revids.coordinate2 = (
                    revids.coordinate2,
                    revids.coordinate1,
                )
                if id_source in tmp:
                    tmp[id_source].append(revids)
                else:
                    tmp[id_source] = [revids]
        # source -> list of closest
        lookup = {}
        for k, v in tmp.items():
            lookup[k] = sorted(v, key=lambda x: x.distance)[0:n_neighbors]
        return MultiLookupDistanceCache(lookup=lookup, n_neighbors=n_neighbors)

    @staticmethod
    def from_json(file):
        with data_store.open(file, "r") as f:
            d = json.load(f)
        return MultiLookupDistanceCache(**d)

    def to_json(self, file):
        with data_store.open(file, "w") as f:
            json.dump(self.dict(), f)

    def __len__(self):
        return len(self.lookup)


class GreedyConnectCache(BaseModel):
    """Cache that can be used by the greedy connection model"""

    connected_cache: SingleLookupDistanceCache = None
    unconnected_cache: MultiLookupDistanceCache = None

    @staticmethod
    def from_workspace(
        workspace,
        unconnected_file="school_cache.json",
        connected_file="fiber_cache.json",
    ):
        connected_cache, unconnected_cache = None, None
        if connected_file is not None:
            # check to see if the file exists
            if data_store.file_exists(os.path.join(workspace, connected_file)):
                connected_cache = SingleLookupDistanceCache.from_json(
                    os.path.join(workspace, connected_file)
                )
        if unconnected_file is not None:
            # check to see if the file exists
            if data_store.file_exists(os.path.join(workspace, unconnected_file)):
                unconnected_cache = MultiLookupDistanceCache.from_json(
                    os.path.join(workspace, unconnected_file)
                )
        return GreedyConnectCache(
            connected_cache=connected_cache, unconnected_cache=unconnected_cache
        )

    def redo_meta(self,connected,schools):
        meta = connected[0]
        lookup = {}
        for s in schools:
            if not s.connected:
                lookup[s.giga_id] = PairwiseDistance(
                    pair_ids = (s.giga_id,meta.coordinate_id),
                    distance = s.fiber_node_distance,
                    distance_type = "euclidean",
                    coordinate1 = s.to_coordinates(),
                    coordinate2 = meta,
                )
        if len(connected)==1:
            self.connected_cache.lookup = lookup
            return

        for s in schools:
            if not s.connected:
                for i in range(1,len(connected)):
                    d = DEFAULT_DISTANCE_FN(s.to_coordinates().coordinate,connected[i].coordinate)
                    if s.giga_id not in lookup:
                        lookup[s.giga_id] = PairwiseDistance(
                            pair_ids = (s.giga_id,connected[i].coordinate_id),
                            distance = d,
                            distance_type = "euclidean",
                            coordinate1 = s.to_coordinates(),
                            coordinate2 = connected[i],
                        )
                    elif d < lookup[s.giga_id].distance:
                        lookup[s.giga_id] = PairwiseDistance(
                            pair_ids = (s.giga_id,connected[i].coordinate_id),
                            distance = d,
                            distance_type = "euclidean",
                            coordinate1 = s.to_coordinates(),
                            coordinate2 = connected[i],
                        )
        self.connected_cache.lookup = lookup
    
    def redo_schools(self,connected,k,schools):
        #lookup = {}
        for s in schools:
            if not s.connected:
                for i in range(k,len(connected)):
                    d = DEFAULT_DISTANCE_FN(s.to_coordinates().coordinate,connected[i].coordinate)
                    if s.giga_id not in self.connected_cache.lookup:
                        self.connected_cache.lookup[s.giga_id] = PairwiseDistance(
                            pair_ids = (s.giga_id,connected[i].coordinate_id),
                            distance = d,
                            distance_type = "euclidean",
                            coordinate1 = s.to_coordinates(),
                            coordinate2 = connected[i],
                        )
                    elif d < self.connected_cache.lookup[s.giga_id].distance:
                        self.connected_cache.lookup[s.giga_id] = PairwiseDistance(
                            pair_ids = (s.giga_id,connected[i].coordinate_id),
                            distance = d,
                            distance_type = "euclidean",
                            coordinate1 = s.to_coordinates(),
                            coordinate2 = connected[i],
                        )
        #self.connected_cache.lookup = lookup

    def __len__(self):
        return len(self.connected_cache or []) + len(self.unconnected_cache or [])
