output "api_app_name" {
  value = azurerm_linux_web_app.api.name
}

output "api_url" {
  value = "https://${azurerm_linux_web_app.api.default_hostname}"
}

output "frontend_app_name" {
  value = azurerm_linux_web_app.frontend.name
}

output "frontend_url" {
  value = "https://${azurerm_linux_web_app.frontend.default_hostname}"
}

output "key_vault_name" {
  value = azurerm_key_vault.portal.name
}

output "postgres_server_name" {
  value = azurerm_postgresql_flexible_server.portal.name
}

output "runtime_identity_client_id" {
  value = data.azurerm_user_assigned_identity.runtime.client_id
}

output "knowledge_base_storage_account_name" {
  value = azurerm_storage_account.knowledge_base.name
}

output "knowledge_base_container_name" {
  value = azurerm_storage_container.knowledge_base.name
}

output "application_gateway_public_ip" {
  value = data.azurerm_public_ip.application_gateway.ip_address
}

output "portal_url" {
  value = var.application_gateway_enabled ? "https://${local.application_gateway_hostname}" : "https://${azurerm_linux_web_app.frontend.default_hostname}"
}

output "application_gateway_fqdn" {
  value = data.azurerm_public_ip.application_gateway.fqdn
}
