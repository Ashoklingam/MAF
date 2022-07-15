import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.preprocessing import StandardScaler
from math import radians
from sklearn.neighbors import NearestNeighbors, DistanceMetric
import numpy as np
from flask import jsonify
# from azure.storage.blob import BlockBlobService
from dotenv import load_dotenv
import openpyxl

load_dotenv()

ROE = 6373.0  # Radius of earth.
dist = DistanceMetric.get_metric('haversine')

# Encoding the age using the range
def encoding_user_age(df: pd.DataFrame):
    df.loc[df['userAge'].between(0, 18), 'age'] = 0
    df.loc[df['userAge'].between(19, 24), 'age'] = 1
    df.loc[df['userAge'].between(25, 34), 'age'] = 2
    df.loc[df['userAge'].between(35, 44), 'age'] = 3
    df.loc[df['userAge'].between(45, 54), 'age'] = 4
    df.loc[df['userAge'].between(55, 64), 'age'] = 5
    df.loc[df['userAge'].gt(64), 'age'] = 6
    df.drop(['userAge'], axis=1, inplace=True)
    df.rename(columns={'age': 'userAge'}, inplace=True)
    return df

# Function for calculating the distance using
def calculate_the_distance(client_data, coords):
    df_list = []
    client_data['distance_km'] = 0
    for rows in client_data.itertuples(index=False):
        location = [[radians(coords[0]), radians(coords[1])],
                    [radians(rows.geo_location_lat), radians(rows.geo_location_long)]]
        distance = np.array(ROE * dist.pairwise(location)).item(1)
        rows = rows._replace(distance_km=distance)
        df_list.append(rows)
    return pd.DataFrame(df_list)

def download_data():
    # ACCOUNT_STORAGE_NAME = os.environ.get('azurestorageaccountname')
    # ACCOUNT_KEY = os.environ.get('azurestorageaccountkey')
    # block_blob_service = BlockBlobService(account_name=ACCOUNT_STORAGE_NAME,
    #                                       account_key=ACCOUNT_KEY)
    # container_name = os.getenv('containername')
    # blob_name = f"{os.getenv('BUSINESS_CLIENT')}/lookalike/lookalike-data.xz"
    # dataset_name = "lookalike-data.xz"
    # full_path_to_file = os.path.join('/tmp', dataset_name)
    # block_blob_service.get_blob_to_path(container_name,
    #                                     blob_name,
    #                                     full_path_to_file)
    # dataset = pd.read_csv(full_path_to_file, compression='xz')
    # return dataset

    dataset = pd.read_csv('./lookalike-data.xz',compression='xz')
    return dataset


def lookalike_model(audiences: str, size: int, coords: tuple, distance: int):
    try:
        client_data = download_data()
        # print('client_data',dict(client_data['audiences']))
        # client_data.to_excel('client_data.xlsx')
        client_data = calculate_the_distance(client_data, coords=coords)
        # print('calculate_distance',client_data.head())
        # client_data.to_excel('calculate_distance.xlsx')
        client_data.drop(['geo_location_lat', 'geo_location_long'], inplace=True, axis=1)
        client_data.rename(columns={'_0': '_id'}, inplace=True)
        client_data.replace('', 0, inplace=True)
        client_data.fillna(0, inplace=True)

        # Select the seed audiences based on the given audiences id
        seed_audiences = client_data[client_data['audiences'].str.contains(audiences)]

        # print('seed_audiences',seed_audiences.head())
        if seed_audiences.shape[0] == 0:
            return jsonify({"code": 500, "message": "The audience have no seed data"})

        seed_audiences = seed_audiences.set_index('_id')
        seed_audiences.drop(['audiences', 'distance_km'], inplace=True, axis=1)
        # print('seed_audiences',seed_audiences)

        # Selecting the pool audiences based on the given distance
        client_data = client_data[client_data['distance_km'] <= distance]
        client_data.reset_index(inplace=True, drop=True)
        client_data.drop(['distance_km'], inplace=True, axis=1)
        client_data.fillna(0, inplace=True)

        # Select the pool audience
        pool_audiences = client_data[~(client_data['audiences'].str.contains(audiences, case=True, regex=True))]
        # print('pool_audiences',pool_audiences)
        pool_audiences = pool_audiences.set_index('_id')
        pool_audiences.drop(['audiences'], inplace=True, axis=1)

        # Applying the StandardScaler function for both pool_audience and seed_audience data
        scaled_pool_audiences = StandardScaler().fit_transform(pool_audiences.values)
        pool_audiences_df = pd.DataFrame(scaled_pool_audiences, index=pool_audiences.index,
                                         columns=pool_audiences.columns)



        scaled_seed_audiences = StandardScaler().fit_transform(seed_audiences.values)
        seed_audiences_df = pd.DataFrame(scaled_seed_audiences, index=seed_audiences.index,
                                         columns=seed_audiences.columns)


        # Creating spark matrix for the pool_audiences data
        pool_matrix = csr_matrix(pool_audiences_df)

        # Building the KNN model using the features
        model_knn = NearestNeighbors(algorithm='kd_tree', n_neighbors=15)
        model_knn.fit(pool_matrix)

        # Calculated the distance and indices of each neighbours values of seed audience
        knn_distances, knn_indices = model_knn.kneighbors(seed_audiences_df)

        # Getting the lookalike audience for the given seed audience
        look_a_score = []
        for i in range(0, len(knn_distances.flatten())):
            look_a_id = {'client_id': pool_audiences.index[knn_indices.flatten()[i]],
                         'score': knn_distances.flatten()[i]}
            look_a_score.append(look_a_id)

        score = pd.DataFrame(look_a_score)
        score = score.sort_values('score')
        score.drop_duplicates(subset=['client_id'], keep='first', inplace=True, ignore_index=False)
        score = score.sort_values('score')
        output = score['client_id'][:size].to_list()
        print('looka_id',output)
        output = [str(x) for x in output]
        return jsonify({"code": 200, "lookalike audiences": output})
    except Exception as ex:
        return jsonify({"code": 500, "message": str(ex)})

if __name__=="__main__":
    "run server"
    audience_id="5db02ca856cd963e00209856"
    size=3000
    distance=900
    lat=47.17431819999999
    long=27.5522608
    coords = (lat, long)
    result=lookalike_model(audience_id, size, coords, distance).json()
    print('result',result)

