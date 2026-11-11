resource "azurerm_cognitive_account" "foundry" {
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

# Cognitive Services reports creation before project management is always ready.
# This bounded wait avoids the transient 409 returned by an immediate project create.
resource "time_sleep" "foundry_project_readiness" {
  depends_on      = [azurerm_cognitive_account.foundry]
  create_duration = "75s"
}

resource "azurerm_cognitive_account_project" "portal" {
  name                 = "mmaug-school-portal"
  cognitive_account_id = azurerm_cognitive_account.foundry.id
  location             = var.location
  display_name         = "MMAUG School Portal"
  description          = "Role-aware school guidance agents grounded in approved MMAUG content."

  identity {
    type = "SystemAssigned"
  }

  depends_on = [time_sleep.foundry_project_readiness]
}

resource "azurerm_cognitive_deployment" "gpt_5_4_mini" {
  name                 = "gpt-5.4-mini"
  cognitive_account_id = azurerm_cognitive_account.foundry.id

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

locals {
  foundry_project_endpoint = "https://${azurerm_cognitive_account.foundry.custom_subdomain_name}.services.ai.azure.com/api/projects/${azurerm_cognitive_account_project.portal.name}"
}
