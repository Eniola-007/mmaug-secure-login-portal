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
  description = "Client ID of the Entra API app registration. The zero UUID supports infrastructure-first deployment before administrator handoff."
  type        = string
  default     = "00000000-0000-0000-0000-000000000000"
}

variable "entra_spa_client_id" {
  description = "Client ID of the Entra SPA app registration. The zero UUID supports infrastructure-first deployment before administrator handoff."
  type        = string
  default     = "00000000-0000-0000-0000-000000000000"
}

variable "azure_ai_project_endpoint" {
  description = "Microsoft Foundry project endpoint. Empty keeps the guarded local assistant fallback active."
  type        = string
  default     = ""
}

variable "azure_ai_model_deployment_name" {
  description = "Approved Microsoft Foundry model deployment used by the role agents."
  type        = string
  default     = "gpt-5.4-mini"
}

variable "azure_ai_public_agent_id" {
  description = "Versioned Foundry prompt-agent name for unauthenticated visitor guidance."
  type        = string
  default     = ""
}

variable "azure_ai_student_agent_id" {
  description = "Versioned Foundry prompt-agent name for the student experience."
  type        = string
  default     = ""
}

variable "azure_ai_teacher_agent_id" {
  description = "Versioned Foundry prompt-agent name for the teacher experience."
  type        = string
  default     = ""
}

variable "azure_ai_admin_agent_id" {
  description = "Versioned Foundry prompt-agent name for the administrator experience."
  type        = string
  default     = ""
}

variable "azure_ad_client_id" {
  description = "Client ID of the administrator-approved service principal used only for Foundry calls."
  type        = string
  default     = ""
}

variable "azure_ad_tenant_id" {
  description = "Tenant ID of the administrator-approved Foundry service principal."
  type        = string
  default     = ""
}

variable "azure_ad_client_secret" {
  description = "Client secret of the administrator-approved Foundry service principal. Written directly to Key Vault."
  type        = string
  default     = ""
  sensitive   = true
}

variable "postgres_admin_login" {
  description = "PostgreSQL bootstrap administrator login."
  type        = string
  default     = "mmaugpgadmin"
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
