variable "subscription_id" {
  description = "Azure subscription that contains the project resource group."
  type        = string
}

variable "tenant_id" {
  description = "Microsoft Entra tenant ID."
  type        = string
}

variable "resource_group_name" {
  description = "Existing project resource group."
  type        = string
  default     = "rg_mmaug_high_school"
}

variable "location" {
  description = "Azure region for project resources."
  type        = string
  default     = "northeurope"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "development"

  validation {
    condition     = contains(["development", "uat", "production"], var.environment)
    error_message = "environment must be development, uat, or production."
  }
}

variable "runtime_identity_name" {
  description = "Existing user-assigned managed identity attached to the backend."
  type        = string
  default     = "id-mmaug-secure-login-portal"
}

variable "entra_api_client_id" {
  description = "Client ID of the Entra API app registration."
  type        = string
}

variable "entra_spa_client_id" {
  description = "Client ID of the Entra SPA app registration."
  type        = string
}

variable "postgres_admin_login" {
  description = "PostgreSQL bootstrap administrator login."
  type        = string
  default     = "mmaugpgadmin"
}

variable "postgres_admin_password" {
  description = "PostgreSQL bootstrap password. Supply through a protected environment secret."
  type        = string
  sensitive   = true
}

variable "app_service_sku" {
  description = "Linux App Service Plan SKU. B1 is for development only."
  type        = string
  default     = "B1"
}

variable "application_gateway_enabled" {
  description = "Create the approved WAF_v2 Application Gateway after DNS and TLS inputs are available."
  type        = bool
  default     = false
}

variable "application_gateway_host_name" {
  description = "Optional custom DNS host name. When empty, the Azure-provided cloudapp.azure.com hostname is used."
  type        = string
  default     = ""
}

variable "application_gateway_dns_label" {
  description = "Azure Public IP DNS label. The resulting regional cloudapp.azure.com name must remain available until deployment."
  type        = string
  default     = "mmaug-secure-portal"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,61}[a-z0-9]$", var.application_gateway_dns_label))
    error_message = "application_gateway_dns_label must be a valid Azure regional DNS label."
  }
}

variable "application_gateway_certificate_secret_id" {
  description = "Versionless Key Vault secret ID for the Application Gateway TLS certificate."
  type        = string
  default     = ""
  sensitive   = true
}

variable "postgres_sku" {
  description = "PostgreSQL Flexible Server SKU. Burstable is for development only."
  type        = string
  default     = "B_Standard_B1ms"
}

variable "tags" {
  description = "Additional resource tags."
  type        = map(string)
  default     = {}
}
