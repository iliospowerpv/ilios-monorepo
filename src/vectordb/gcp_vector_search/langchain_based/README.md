# Index deployment and usage

## Deployment

Use create_new_index.ipynb notebook and run it with config parameters. It will create a new index and deploy it to the 
specified location using specified Storage Bucket - the bucket must be empty before deployment. Storage bucket and 
Index has to be created in the same region. The deployment is using Langchain logic to create the index, it has some 
specific algorithm for indexing and searching.

## Index update

To add new files to the index, use update_index.ipynb notebook. It will update the index with new file chunks and 
deploy it to the Storage Bucket, dedicated to the index. You need to deploy the index to en endpoint first and use 
endpoint ID and index ID in the parameters on top of the script. You can find the _index_id_ and _endpoint_id_ in the 
Vector Store Index configuration in GCP Console.