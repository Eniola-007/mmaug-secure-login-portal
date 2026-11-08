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
