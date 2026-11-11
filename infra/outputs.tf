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

output "email_sender_address" {
  value = "donotreply@${azurerm_email_communication_service_domain.portal.from_sender_domain}"
}

output "foundry_project_endpoint" {
  value = local.foundry_project_endpoint
}

output "foundry_model_deployment_name" {
  value = azurerm_cognitive_deployment.gpt_5_4_mini.name
}

output "portal_url" {
  value = "https://${azurerm_linux_web_app.frontend.default_hostname}"
}
