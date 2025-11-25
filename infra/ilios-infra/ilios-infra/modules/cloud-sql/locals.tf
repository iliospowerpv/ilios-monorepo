locals {
  instances_default_config = try(var.cloud_sql_configuration, {})

  instances_configs = {
    for instance_config in local.instances_default_config : instance_config.name => instance_config
  }

  instances_with_random_suffix = {
    for instance_config in local.instances_default_config : instance_config.name => {
      length = instance_config.random_suffix.length
    } if instance_config.random_suffix != null
  }

  instances_with_private_vpc_connection = {
    for instance_config in local.instances_default_config :
    instance_config.name => instance_config.settings.ip_configuration.private_network
    if try(instance_config.settings.ip_configuration.private_network, null) != null
  }

  master_instances_vpc_regiona_pairs = distinct(flatten([for instance_config in local.instances_default_config : {
    vpc    = instance_config.settings.ip_configuration.private_network
    region = instance_config.region
    } if try(instance_config.settings.ip_configuration.private_network, null) != null
  ]))
  /*
  relicas_vpc_regiona_pairs = distinct(flatten([for instance_config in local.instances_default_config :
    [for replica_parameters in instance_config.replicas : {
      vpc    = replica_parameters.settings.ip_configuration.private_network
      region = replica_parameters.region
  } if try(replica_parameters.settings.ip_configuration.private_network, null) != null]]))
*/
  regions_vpc_pairs_iterable = { for vpc_region_pair in // distinct(concat(
    local.master_instances_vpc_regiona_pairs :          //,
    // local.relicas_vpc_regiona_pairs)) :
    "${vpc_region_pair.vpc}:${vpc_region_pair.region}" => vpc_region_pair
  }

  regions_per_vpc = { for vpc_region_pair in   //distinct(concat(
    local.master_instances_vpc_regiona_pairs : //,
    //local.relicas_vpc_regiona_pairs)) :
    vpc_region_pair.vpc => vpc_region_pair.region...
  }

  instance_databases_pairs = flatten([for instance_config in local.instances_default_config :
    [for database in instance_config.databases : {
      instance = instance_config.name
      database = database
  }]])

  databases_iterable = { for database_pair in local.instance_databases_pairs :
    "${database_pair.instance}:${database_pair.database}" => database_pair
  }

  instance_users_pairs = flatten([for instance_config in local.instances_default_config :
    [for user in instance_config.users : {
      instance = instance_config.name
      user     = user
  }]])

  users_iterable = { for user_pair in local.instance_users_pairs :
    "${user_pair.instance}:${user_pair.user}" => user_pair
  }
}
