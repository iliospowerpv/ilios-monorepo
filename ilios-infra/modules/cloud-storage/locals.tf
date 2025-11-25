locals {
  buckets = { for bucket_config in var.buckets : bucket_config.name => bucket_config }

  bucket_iam_members = { for iam_member_role in flatten([
    for bucket_config in local.buckets : [for iam_member in bucket_config.iam_members : [
      for iam_member_role in iam_member.roles : {
        bucket = bucket_config.name
        name   = iam_member.name
        role   = iam_member_role
    }]]
    ]) : "${iam_member_role.bucket}:${iam_member_role.name}:${iam_member_role.role}" => iam_member_role
  }

  cdn = { for storage in var.buckets :
    storage.name => can(storage.cdn.name) ? { name = storage.cdn.name } : {} if can(storage.cdn)
  }

  cdn_list = [
    for storage in var.buckets :
    can(storage.cdn.name) ? {
      bucket = storage.name
      name   = storage.cdn.name
    } : {}
  ]


}


