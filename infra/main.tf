data "azurerm_client_config" "current" {}

data "azurerm_resource_group" "project" {
  name = var.resource_group_name
}

data "azurerm_user_assigned_identity" "runtime" {
  name                = var.runtime_identity_name
  resource_group_name = data.azurerm_resource_group.project.name
}

resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
}

resource "random_password" "postgres" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}:?"

  keepers = {
    security_rotation = "2026-11-09-alembic-log"
  }
}

resource "random_password" "local_auth_jwt" {
  length  = 64
  special = false
}

locals {
  prefix = "mmaug-${var.environment}"
  suffix = random_string.suffix.result
  common_tags = merge(
    {
      project     = "mmaug-secure-login-portal"
      environment = var.environment
      managed-by  = "terraform"
      data-class  = "synthetic"
    },
    var.tags
  )
}

resource "azurerm_storage_account" "knowledge_base" {
  name                             = "stmmaugkb${local.suffix}"
  resource_group_name              = data.azurerm_resource_group.project.name
  location                         = var.location
  account_tier                     = "Standard"
  account_replication_type         = "LRS"
  min_tls_version                  = "TLS1_2"
  allow_nested_items_to_be_public  = false
  cross_tenant_replication_enabled = false
  tags                             = local.common_tags
}

resource "azurerm_storage_container" "knowledge_base" {
  name                  = "knowledge-base"
  storage_account_id    = azurerm_storage_account.knowledge_base.id
  container_access_type = "private"
}

resource "azurerm_virtual_network" "portal" {
  name                = "vnet-${local.prefix}-${local.suffix}"
  address_space       = ["10.42.0.0/16"]
  location            = var.location
  resource_group_name = data.azurerm_resource_group.project.name
  tags                = local.common_tags
}

resource "azurerm_subnet" "apps" {
  name                 = "snet-appservice"
  resource_group_name  = data.azurerm_resource_group.project.name
  virtual_network_name = azurerm_virtual_network.portal.name
  address_prefixes     = ["10.42.1.0/24"]

  delegation {
    name = "app-service-delegation"
    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

resource "azurerm_subnet" "database" {
  name                 = "snet-postgresql"
  resource_group_name  = data.azurerm_resource_group.project.name
  virtual_network_name = azurerm_virtual_network.portal.name
  address_prefixes     = ["10.42.2.0/24"]
  service_endpoints    = ["Microsoft.Storage"]

  delegation {
    name = "postgres-delegation"
    service_delegation {
      name    = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_subnet" "application_gateway" {
  count = var.application_gateway_enabled ? 1 : 0

  name                 = "snet-appgateway"
  resource_group_name  = data.azurerm_resource_group.project.name
  virtual_network_name = azurerm_virtual_network.portal.name
  address_prefixes     = ["10.42.3.0/24"]
}

resource "azurerm_private_dns_zone" "postgres" {
  name                = "privatelink.postgres.database.azure.com"
  resource_group_name = data.azurerm_resource_group.project.name
  tags                = local.common_tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgres" {
  name                  = "postgres-vnet-link"
  private_dns_zone_name = azurerm_private_dns_zone.postgres.name
  virtual_network_id    = azurerm_virtual_network.portal.id
  resource_group_name   = data.azurerm_resource_group.project.name
  tags                  = local.common_tags
}

resource "azurerm_log_analytics_workspace" "portal" {
  name                = "log-${local.prefix}-${local.suffix}"
  location            = var.location
  resource_group_name = data.azurerm_resource_group.project.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  daily_quota_gb      = 1
  tags                = local.common_tags
}

resource "azurerm_application_insights" "portal" {
  name                 = "appi-${local.prefix}-${local.suffix}"
  location             = var.location
  resource_group_name  = data.azurerm_resource_group.project.name
  workspace_id         = azurerm_log_analytics_workspace.portal.id
  application_type     = "web"
  daily_data_cap_in_gb = 1
  tags                 = local.common_tags
}

resource "azurerm_key_vault" "portal" {
  name                       = "kv-mmaug-${local.suffix}"
  location                   = var.location
  resource_group_name        = data.azurerm_resource_group.project.name
  tenant_id                  = var.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = false
  purge_protection_enabled   = var.environment == "production"
  soft_delete_retention_days = 7
  tags                       = local.common_tags

  access_policy {
    tenant_id = var.tenant_id
    object_id = data.azurerm_user_assigned_identity.runtime.principal_id

    secret_permissions      = ["Get", "List", "Set", "Delete", "Recover"]
    certificate_permissions = ["Get", "List", "Create", "Import", "Update", "Delete", "Recover"]
  }

  dynamic "access_policy" {
    for_each = data.azurerm_client_config.current.object_id == data.azurerm_user_assigned_identity.runtime.principal_id ? [] : [data.azurerm_client_config.current.object_id]

    content {
      tenant_id = var.tenant_id
      object_id = access_policy.value

      secret_permissions      = ["Get", "List", "Set", "Delete", "Recover"]
      certificate_permissions = ["Get", "List", "Create", "Import", "Update", "Delete", "Recover"]
    }
  }
}

resource "azurerm_postgresql_flexible_server" "portal" {
  name                          = "psql-${local.prefix}-${local.suffix}"
  resource_group_name           = data.azurerm_resource_group.project.name
  location                      = var.location
  zone                          = "1"
  version                       = "16"
  delegated_subnet_id           = azurerm_subnet.database.id
  private_dns_zone_id           = azurerm_private_dns_zone.postgres.id
  public_network_access_enabled = false
  administrator_login           = var.postgres_admin_login
  administrator_password        = random_password.postgres.result
  sku_name                      = var.postgres_sku
  storage_mb                    = 32768
  auto_grow_enabled             = true
  backup_retention_days         = var.environment == "production" ? 14 : 7
  geo_redundant_backup_enabled  = var.environment == "production"
  tags                          = local.common_tags

  depends_on = [azurerm_private_dns_zone_virtual_network_link.postgres]
}

resource "azurerm_postgresql_flexible_server_database" "portal" {
  name      = "mmaug_portal"
  server_id = azurerm_postgresql_flexible_server.portal.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

resource "azurerm_key_vault_secret" "database_url" {
  name = "DATABASE-URL"
  value_wo = format(
    "postgresql+psycopg://%s:%s@%s:5432/%s?sslmode=require&connect_timeout=15",
    var.postgres_admin_login,
    urlencode(random_password.postgres.result),
    azurerm_postgresql_flexible_server.portal.fqdn,
    azurerm_postgresql_flexible_server_database.portal.name
  )
  value_wo_version = 3
  key_vault_id     = azurerm_key_vault.portal.id

}

resource "azurerm_key_vault_secret" "local_auth_jwt" {
  name             = "LOCAL-AUTH-JWT-SECRET"
  value_wo         = random_password.local_auth_jwt.result
  value_wo_version = 1
  key_vault_id     = azurerm_key_vault.portal.id
}

resource "azurerm_key_vault_secret" "foundry_client_secret" {
  count = trimspace(var.azure_ad_client_id) != "" ? 1 : 0

  name             = "FOUNDRY-CLIENT-SECRET"
  value_wo         = var.azure_ad_client_secret
  value_wo_version = 1
  key_vault_id     = azurerm_key_vault.portal.id

  lifecycle {
    precondition {
      condition = (
        trimspace(var.azure_ad_tenant_id) != "" &&
        trimspace(var.azure_ad_client_secret) != ""
      )
      error_message = "AZURE_AD_TENANT_ID and AZURE_AD_CLIENT_SECRET are required when AZURE_AD_CLIENT_ID is configured."
    }
  }
}

resource "azurerm_service_plan" "portal" {
  name                = "asp-${local.prefix}-${local.suffix}"
  resource_group_name = data.azurerm_resource_group.project.name
  location            = var.location
  os_type             = "Linux"
  sku_name            = var.app_service_sku
  tags                = local.common_tags
}

resource "azurerm_linux_web_app" "api" {
  name                                           = "app-${local.prefix}-api-${local.suffix}"
  resource_group_name                            = data.azurerm_resource_group.project.name
  location                                       = var.location
  service_plan_id                                = azurerm_service_plan.portal.id
  https_only                                     = true
  ftp_publish_basic_authentication_enabled       = false
  webdeploy_publish_basic_authentication_enabled = false
  virtual_network_subnet_id                      = azurerm_subnet.apps.id
  key_vault_reference_identity_id                = data.azurerm_user_assigned_identity.runtime.id

  identity {
    type         = "UserAssigned"
    identity_ids = [data.azurerm_user_assigned_identity.runtime.id]
  }

  site_config {
    always_on                         = var.app_service_sku != "F1"
    app_command_line                  = "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
    ftps_state                        = "Disabled"
    minimum_tls_version               = "1.2"
    vnet_route_all_enabled            = true
    health_check_path                 = "/health/ready"
    health_check_eviction_time_in_min = 5
    application_stack {
      python_version = "3.12"
    }
  }

  app_settings = merge({
    ENVIRONMENT              = var.environment
    DATABASE_URL             = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.database_url.versionless_id})"
    ENTRA_TENANT_ID          = var.tenant_id
    ENTRA_AUTHORITY_TENANT   = "common"
    ENTRA_API_CLIENT_ID      = var.entra_api_client_id
    ENTRA_REQUIRED_SCOPE     = "access_as_user"
    ALLOW_DEV_AUTH           = "false"
    LOCAL_AUTH_JWT_SECRET    = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.local_auth_jwt.versionless_id})"
    LOCAL_AUTH_TOKEN_MINUTES = "60"
    CORS_ORIGINS = jsonencode([
      var.application_gateway_enabled ? "https://${local.application_gateway_hostname}" : "https://${azurerm_linux_web_app.frontend.default_hostname}"
    ])
    APPLICATIONINSIGHTS_CONNECTION_STRING      = azurerm_application_insights.portal.connection_string
    ApplicationInsightsAgent_EXTENSION_VERSION = "~3"
    AZURE_CLIENT_ID                            = data.azurerm_user_assigned_identity.runtime.client_id
    AZURE_AD_CLIENT_ID                         = var.azure_ad_client_id
    AZURE_AD_TENANT_ID                         = var.azure_ad_tenant_id
    AZURE_AI_PROJECT_ENDPOINT                  = var.azure_ai_project_endpoint
    AZURE_AI_MODEL_DEPLOYMENT_NAME             = var.azure_ai_model_deployment_name
    AZURE_AI_STUDENT_AGENT_ID                  = var.azure_ai_student_agent_id
    AZURE_AI_TEACHER_AGENT_ID                  = var.azure_ai_teacher_agent_id
    AZURE_AI_ADMIN_AGENT_ID                    = var.azure_ai_admin_agent_id
    KNOWLEDGE_BASE_STORAGE_URL                 = azurerm_storage_account.knowledge_base.primary_blob_endpoint
    KNOWLEDGE_BASE_CONTAINER                   = azurerm_storage_container.knowledge_base.name
    SCM_DO_BUILD_DURING_DEPLOYMENT             = "false"
    ENABLE_ORYX_BUILD                          = "false"
    PYTHONPATH                                 = "/home/site/wwwroot/.python_packages/lib/site-packages"
    WEBSITES_CONTAINER_START_TIME_LIMIT        = "600"
    WEBSITES_PORT                              = "8000"
    }, trimspace(var.azure_ad_client_id) != "" ? {
    AZURE_AD_CLIENT_SECRET = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.foundry_client_secret[0].versionless_id})"
  } : {})

  tags = local.common_tags
}

resource "azurerm_linux_web_app" "frontend" {
  name                                           = "app-${local.prefix}-web-${local.suffix}"
  resource_group_name                            = data.azurerm_resource_group.project.name
  location                                       = var.location
  service_plan_id                                = azurerm_service_plan.portal.id
  https_only                                     = true
  ftp_publish_basic_authentication_enabled       = false
  webdeploy_publish_basic_authentication_enabled = false

  site_config {
    always_on           = var.app_service_sku != "F1"
    ftps_state          = "Disabled"
    minimum_tls_version = "1.2"
    app_command_line    = "python -m http.server 8000 --directory /home/site/wwwroot"
    application_stack {
      python_version = "3.12"
    }
  }

  app_settings = {
    APPLICATIONINSIGHTS_CONNECTION_STRING      = azurerm_application_insights.portal.connection_string
    ApplicationInsightsAgent_EXTENSION_VERSION = "~3"
    SCM_DO_BUILD_DURING_DEPLOYMENT             = "false"
    ENABLE_ORYX_BUILD                          = "false"
    WEBSITES_CONTAINER_START_TIME_LIMIT        = "600"
    WEBSITES_PORT                              = "8000"
  }

  tags = local.common_tags
}
