import geopandas as gpd
import pandas as pd
import networkx as nx
from typing import Union


def remove_deadends(gdf: Union[gpd.GeoDataFrame, pd.DataFrame]):
    """
    Removes the last link in all sets of links in gdf leading to a deadend.


    Args:
        gdf : List of links in a network. Must contain 'a' and 'b' columns.

    Returns:
        gdf: Input gdf with dead ends removed.
    """
    graph = nx.Graph()
    graph.add_edges_from(gdf[["a", "b"]].values)
    df = pd.DataFrame(graph.degree, columns=["N", "degree"])
    droppers = df[df["degree"] == 1]
    if len(droppers) == 0:
        return gdf
    gdf = gdf.loc[(~gdf["a"].isin(droppers["N"])) & (~gdf["b"].isin(droppers["N"]))]
    return gdf


def recursive_deadends(gdf, iter_lim: int):
    """
    Calls 'remove_deadends' recursively to remove entire series of links forming dead ends.
    Args:
        gdf (_type_): The gdf to be trimmed. Must contain 'a' and 'b' columns.

    Returns:
        A trimmed geodataframe or dataframe, the type will be the same as the input.
    """
    i = 1
    while True:
        new_gdf = remove_deadends(gdf)
        if gdf.equals(new_gdf):
            return gdf, i
        gdf = new_gdf
        i += 1
        if i > iter_lim:
            break


if __name__ == "__main__":
    itn = gpd.read_file(r"I:\Transfer\IS\ITN\TMJT_network.shp")
    trimmed, iters = recursive_deadends(itn, 50)
    print(f"Network trimmed in {iters} iterations.")
    trimmed.to_file(r"I:\Transfer\IS\ITN\trimmed_itn")
