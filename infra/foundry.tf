moved {
  from = azurerm_cognitive_account.foundry
  to   = azurerm_cognitive_account.foundry_legacy
}

moved {
  from = time_sleep.foundry_project_readiness
  to   = time_sleep.foundry_legacy_project_readiness
}

moved {
  from = azurerm_cognitive_account_project.portal
  to   = azurerm_cognitive_account_project.portal_legacy
}

moved {
  from = azurerm_cognitive_deployment.gpt_5_4_mini
  to   = azurerm_cognitive_deployment.gpt_5_4_mini_legacy
}

resource "azurerm_cognitive_account" "foundry_legacy" {
  name                       = "aifoundry-${local.prefix}-${local.suffix}"
  resource_group_name        = data.azurerm_resource_group.project.name
  location                   = var.location
  kind                       = "AIServices"
  sku_name                   = "S0"
  custom_subdomain_name      = "aifoundry-${local.prefix}-${local.suffix}"
  project_management_enabled = true
  local_auth_enabled         = false

  identity {
    type = "SystemAssigned"
  }

  tags = local.common_tags
}

resource "time_sleep" "foundry_legacy_project_readiness" {
  depends_on      = [azurerm_cognitive_account.foundry_legacy]
  create_duration = "75s"
}

resource "azurerm_cognitive_account_project" "portal_legacy" {
  name                 = "mmaug-school-portal"
  cognitive_account_id = azurerm_cognitive_account.foundry_legacy.id
  location             = var.location
  display_name         = "MMAUG School Portal"
  description          = "Legacy North Europe Foundry project."

  identity {
    type = "SystemAssigned"
  }

  depends_on = [time_sleep.foundry_legacy_project_readiness]
}

resource "azurerm_cognitive_deployment" "gpt_5_4_mini_legacy" {
  name                 = "gpt-5.4-mini"
  cognitive_account_id = azurerm_cognitive_account.foundry_legacy.id

  model {
    format  = "OpenAI"
    name    = "gpt-5.4-mini"
    version = "2026-03-17"
  }

  sku {
    name     = "GlobalStandard"
    capacity = 1
  }
}

resource "azurerm_cognitive_account" "foundry_agents" {
  name                       = "aifoundry-${local.prefix}-agents-${local.suffix}"
  resource_group_name        = data.azurerm_resource_group.project.name
  location                   = var.foundry_location
  kind                       = "AIServices"
  sku_name                   = "S0"
  custom_subdomain_name      = "aifoundry-${local.prefix}-agents-${local.suffix}"
  project_management_enabled = true
  local_auth_enabled         = false

  identity {
    type = "SystemAssigned"
  }

  tags = local.common_tags
}

resource "time_sleep" "foundry_agents_project_readiness" {
  depends_on      = [azurerm_cognitive_account.foundry_agents]
  create_duration = "75s"
}

resource "azurerm_cognitive_account_project" "portal_agents" {
  name                 = "mmaug-school-portal-agents"
  cognitive_account_id = azurerm_cognitive_account.foundry_agents.id
  location             = var.foundry_location
  display_name         = "MMAUG School Portal Agents"
  description          = "Role-isolated school guidance agents with Foundry File Search."

  identity {
    type = "SystemAssigned"
  }

  depends_on = [time_sleep.foundry_agents_project_readiness]
}

resource "azurerm_cognitive_deployment" "gpt_5_4_mini_agents" {
  name                 = var.azure_ai_model_deployment_name
  cognitive_account_id = azurerm_cognitive_account.foundry_agents.id

  model {
    format  = "OpenAI"
    name    = var.azure_ai_model_deployment_name
    version = "2026-03-17"
  }

  sku {
    name     = "DataZoneStandard"
    capacity = 1
  }
}

locals {
  foundry_project_endpoint = "https://${azurerm_cognitive_account.foundry_agents.custom_subdomain_name}.services.ai.azure.com/api/projects/${azurerm_cognitive_account_project.portal_agents.name}"
}
