# The 'configs' folder

Idea of the directory is to collect configurations, which are manageable via internal APIs.
APIs are unified to read/write json-formatted config file and have the `config_type` query parameter to specify config file to work with.
The json files are the default configs, the long-term management is supported via DB storing.
Read config operation: first try to get config from DB, if not found - get config from file.
Write config operation: save config to DB.

### API management

These are **internal** endpoints, use them wisely.

#### Retrieve config API

Internal get endpoint to read the configuration.

#### Update config API

Internal put endpoint to overwrite the configuration.
The configuration table ensures only single instance of each config exists.

## 1. ai_parsing_config.json

This is the list of agreement types, which are available for mapping, and their keys, in the following structure:
```json
{
  "AGREEMENT_NAME.1": [
    "Key1.1",
    "Key1.N"
  ],
  "AGREEMENT_NAME.N": [
    "KeyN.1",
    "KeyN.N"
  ]
}
```
### Management with APIs

Use endpoint described in the [API management](#api-management) section with `ai_parsing` value for the `config_type` query parameter.

## 2. agreement_names_mapping_config.json

The file represents correspondence between agreement Platform name (how it looks on UI) and agreement Pipeline name (how it's expected from AI engine):
```json
{
  "PLATFORM_NAME.1": "PIPELINE_NAME.1",
  "PLATFORM_NAME.N": "PIPELINE_NAME.N"
}
```
### Management with APIs

Use endpoint described in the [API management](#api-management) section with `agreement_names` value for the `config_type` query parameter.

## 2. co_terminus_config.json

The file describes the list of keys to be compared, the file which use for comparison and the corresponding key name in this file:
```json
{
  "KEY.1": [
    {
      "AGREEMENT_NAME.1": "AGREEMENT_KEY_NAME.1",
      "AGREEMENT_NAME.N": "AGREEMENT_KEY_NAME.N"
    }
  ]
}
```
For example:
```json
{
  "PPA Net Energy Rate": [
    {
      "O&M Agreement": "PPA Net Energy Rate",
      "PPA and Amendments": "Power Purchase Agreement Rate"
    }
  ]
}
```
**Meaning**: we need to do comparison for the `PPA Net Energy Rate` key, which appears as `PPA Net Energy Rate` in the `O&M Agreement` and as `Power Purchase Agreement Rate` in the `PPA and Amendments`.
### Management with APIs

Use endpoint described in the [API management](#api-management) section with `co_terminus` value for the `config_type` query parameter.
