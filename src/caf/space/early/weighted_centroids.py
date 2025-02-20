import pandas as pd
import caf.space as cs


def weighted_centroids(lower_shape: cs.LowerZoneSystemInfo,
                       upper_shape: cs.TransZoneSystemInfo):
    """
    Summary
    -------
    Create centroids based on weighting data.

    Parameters
    ----------

    lower_shape: cs.LowerZoneSystemInfo
        Info on the lower shape used for weighting.
    upper_shape: cs.TransZoneSystemInfo
        Info on shape to produce weighted centroids for.

    Returns
    -------

    pd.DataFrame: A dataframe of centroids, with columns for 'x' and 'y'.
    The zone ids will be in the index.
    """
    trans_conf = cs.ZoningTranslationInputs(zone_1=upper_shape,
                                            zone_2=lower_shape._lower_to_higher()
                                        )
    lookup = cs.ZoneTranslation(trans_conf).spatial_translation(return_gdf=True)
    lower_weight = pd.read_csv(lower_shape.weight_data, index_col=lower_shape.weight_id_col)
    lower_weight.index.name = f"{lower_shape.name}_id"
    cent = lookup.join(lower_weight)
    cent['val'] *= cent[f'{lower_shape.name}_to_{upper_shape.name}']
    cent['x_weight'] = cent.centroid.x * cent[lower_shape.data_col]
    cent['y_weight'] = cent.centroid.y * cent[lower_shape.data_col]
    grouped = cent.groupby(f"{upper_shape.name}_id")[[lower_shape.data_col, 'x_weight', 'y_weight']].sum()
    grouped['x'] = grouped['x_weight'] / grouped[lower_shape.data_col]
    grouped['y'] = grouped['y_weight'] / grouped[lower_shape.data_col]