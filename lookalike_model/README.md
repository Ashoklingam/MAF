Lookalike model:

The lookalike audience model is which predict clients who have similar behaviors based on the given seed audience(set of our clients) 

For training the lookalike ML model we need seed audience(target audience) and Pool audience.
Seed audience:  A group of users who are our clients and share similar interests and behaviors (base customer) and Pool audience: The pool user data, where we look for audiences who are similar behaviors to our seed audience.

To train the ML model in FFR, we use the saved audience from the audience collection (a set of users with similar characteristics such as age, gender, interest, and hobbies) as the seed audience.
We have used all of the users/customer data from the premium auto client for the Pool of Audiences and we have used the KNN algorithm for training the lookalike model and predicting the lookalike audiences

Model deployment:
The model deployment is done in two-part one is the data acquisition and the other is serving 

The data acquisition:  In the data acquisition the is data extraction from the blob MongoDB, applied the data preprocessing,  applied the encoding process, and upload processed data in the Azure blob storage. The data acquisition script is scheduled using the cron that runs every hour.

Serving: Serving trained ML models by deploying the model Docker Image in the AKS cluster using the YAML file and Azure Container Registry.

Each time the API request is made. It takes updated data from Azure blob storage, trains the model, and predicts lookalike audiences for the given seed data.