import geopandas as gpd
from scipy.spatial import cKDTree
import pandas as pd

def find_nearest_points(target_gdf, reference_gdf, identifier_column=None):
    """
    Find the nearest point in the reference GeoDataFrame for each point in the target GeoDataFrame.

    Parameters:
    - target_gdf (GeoDataFrame): GeoDataFrame containing target points.
    - reference_gdf (GeoDataFrame): GeoDataFrame containing reference points.

    Returns:
    - GeoDataFrame: A copy of target_gdf with additional columns:
        'nearest_geometry': geometry of the closest point from reference_gdf
        'distance': distance to the nearest point in reference_gdf
    """
    # Ensure both GeoDataFrames use the same CRS
    if target_gdf.crs != reference_gdf.crs:
        raise ValueError("The CRS of both GeoDataFrames must match.")

    # Extract coordinates
    target_coords = list(zip(target_gdf.geometry.x, target_gdf.geometry.y))
    reference_coords = list(zip(reference_gdf.geometry.x, reference_gdf.geometry.y))

    # Build KDTree for reference points
    tree = cKDTree(reference_coords)

    # Query the tree for nearest neighbor to each target point
    distances, indices = tree.query(target_coords, k=1)

    # Prepare results
    results = target_gdf.copy()
    results['nearest_geometry'] = reference_gdf.iloc[indices].geometry.values
    results['distance'] = distances

    if identifier_column:
        if identifier_column in reference_gdf.columns:
            results[f"{identifier_column}_ref"] = reference_gdf.iloc[indices][identifier_column].values
        else:
            raise ValueError(
                f"'{identifier_column}' is not a column in the reference GeoDataFrame")

    return results


def find_nearest_points_2(target_gdf, reference_gdf, identifier_column=None, n_neighbors=1):
    """
    Find the nearest points in the reference GeoDataFrame for each point in the target GeoDataFrame.

    Parameters:
    - target_gdf (GeoDataFrame): GeoDataFrame containing target points.
    - reference_gdf (GeoDataFrame): GeoDataFrame containing reference points.
    - identifier_column (str, optional): Column name from reference_gdf to add as an identifier in the result.
    - n_neighbors (int): Number of nearest neighbors to find.

    Returns:
    - GeoDataFrame: A copy of target_gdf with additional columns for each neighbor:
        - 'nearest_geometry_i': geometry of the i-th closest point from reference_gdf
        - 'distance_i': distance to the i-th nearest point in reference_gdf
        - '[identifier_column]_i': value of the identifier column for the i-th nearest point in reference_gdf (if provided)
    """
    # Ensure both GeoDataFrames use the same CRS
    if target_gdf.crs != reference_gdf.crs:
        raise ValueError("The CRS of both GeoDataFrames must match.")

    # Extract coordinates
    target_coords = list(zip(target_gdf.geometry.x, target_gdf.geometry.y))
    reference_coords = list(zip(reference_gdf.geometry.x, reference_gdf.geometry.y))

    # Build KDTree for reference points
    tree = cKDTree(reference_coords)

    # Query the tree for the n nearest neighbors to each target point
    distances, indices = tree.query(target_coords, k=n_neighbors)

    # Prepare results DataFrame
    results = target_gdf.copy()

    # Handle single vs multiple neighbors (cKDTree returns different shapes based on n_neighbors)
    if n_neighbors == 1:
        # Convert single nearest neighbor to arrays to handle consistently
        distances = distances[:, None]
        indices = indices[:, None]

    # Iterate over each neighbor to add columns
    for i in range(n_neighbors):
        # Geometry and distance of the i-th nearest neighbor
        results[f'nearest_geometry_{i + 1}'] = reference_gdf.iloc[indices[:, i]].geometry.values
        results[f'distance_{i + 1}'] = distances[:, i]

        # Identifier column for the i-th nearest neighbor (if specified)
        if identifier_column:
            if identifier_column in reference_gdf.columns:
                results[f'{identifier_column}_{i + 1}'] = reference_gdf.iloc[indices[:, i]][
                    identifier_column].values
            else:
                raise ValueError(
                    f"'{identifier_column}' is not a column in the reference GeoDataFrame")

    # If performing self-matching, filter out self as nearest neighbor (distance == 0)
    if target_gdf is reference_gdf:
        # Set distance and geometry of self-nearest neighbors to None/NaN
        for i in range(n_neighbors):
            self_mask = (distances[:, i] == 0)
            results.loc[self_mask, f'nearest_geometry_{i + 1}'] = None
            results.loc[self_mask, f'distance_{i + 1}'] = float('nan')
            if identifier_column:
                results.loc[self_mask, f'{identifier_column}_{i + 1}'] = None

    return results

if __name__ == '__main__':
    hw_node = gpd.read_file(r"I:\Transfer\IS\supply\oshw_node.shp")
    pt_node = gpd.read_file(r"I:\Transfer\IS\supply\PTnetwork_stop.shp")
    nearest = find_nearest_points_2(pt_node, pt_node, 'n', 2)