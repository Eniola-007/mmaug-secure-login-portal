locals {
  application_gateway_name = "agw-${local.prefix}-${local.suffix}"
}

resource "azurerm_public_ip" "application_gateway" {
  count = var.application_gateway_enabled ? 1 : 0

  name                = "pip-${local.application_gateway_name}"
  resource_group_name = data.azurerm_resource_group.project.name
  location            = var.location
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = local.common_tags
}

resource "azurerm_web_application_firewall_policy" "portal" {
  count = var.application_gateway_enabled ? 1 : 0

  name                = "waf-${local.prefix}-${local.suffix}"
  resource_group_name = data.azurerm_resource_group.project.name
  location            = var.location
  tags                = local.common_tags

  policy_settings {
    enabled                     = true
    mode                        = "Prevention"
    request_body_check          = true
    max_request_body_size_in_kb = 128
    file_upload_limit_in_mb     = 10
  }

  managed_rules {
    managed_rule_set {
      type    = "OWASP"
      version = "3.2"
    }
  }
}

resource "azurerm_application_gateway" "portal" {
  count = var.application_gateway_enabled ? 1 : 0

  name                = local.application_gateway_name
  resource_group_name = data.azurerm_resource_group.project.name
  location            = var.location
  firewall_policy_id  = azurerm_web_application_firewall_policy.portal[0].id
  http2_enabled       = true
  tags                = local.common_tags

  identity {
    type         = "UserAssigned"
    identity_ids = [data.azurerm_user_assigned_identity.runtime.id]
  }

  sku {
    name = "WAF_v2"
    tier = "WAF_v2"
  }

  autoscale_configuration {
    min_capacity = 1
    max_capacity = 2
  }

  gateway_ip_configuration {
    name      = "gateway-ip"
    subnet_id = azurerm_subnet.application_gateway[0].id
  }

  frontend_ip_configuration {
    name                 = "public-ip"
    public_ip_address_id = azurerm_public_ip.application_gateway[0].id
  }

  frontend_port {
    name = "http"
    port = 80
  }

  frontend_port {
    name = "https"
    port = 443
  }

  backend_address_pool {
    name  = "frontend"
    fqdns = [azurerm_linux_web_app.frontend.default_hostname]
  }

  backend_address_pool {
    name  = "api"
    fqdns = [azurerm_linux_web_app.api.default_hostname]
  }

  probe {
    name                                      = "frontend-health"
    protocol                                  = "Https"
    path                                      = "/"
    interval                                  = 30
    timeout                                   = 30
    unhealthy_threshold                       = 3
    pick_host_name_from_backend_http_settings = true
  }

  probe {
    name                                      = "api-health"
    protocol                                  = "Https"
    path                                      = "/health/live"
    interval                                  = 30
    timeout                                   = 30
    unhealthy_threshold                       = 3
    pick_host_name_from_backend_http_settings = true
  }

  backend_http_settings {
    name                                = "frontend-https"
    cookie_based_affinity               = "Disabled"
    port                                = 443
    protocol                            = "Https"
    request_timeout                     = 30
    pick_host_name_from_backend_address = true
    probe_name                          = "frontend-health"
  }

  backend_http_settings {
    name                                = "api-https"
    cookie_based_affinity               = "Disabled"
    port                                = 443
    protocol                            = "Https"
    request_timeout                     = 30
    pick_host_name_from_backend_address = true
    probe_name                          = "api-health"
  }

  ssl_certificate {
    name                = "portal-certificate"
    key_vault_secret_id = var.application_gateway_certificate_secret_id
  }

  http_listener {
    name                           = "https"
    frontend_ip_configuration_name = "public-ip"
    frontend_port_name             = "https"
    protocol                       = "Https"
    host_name                      = var.application_gateway_host_name
    require_sni                    = true
    ssl_certificate_name           = "portal-certificate"
  }

  http_listener {
    name                           = "http"
    frontend_ip_configuration_name = "public-ip"
    frontend_port_name             = "http"
    protocol                       = "Http"
    host_name                      = var.application_gateway_host_name
  }

  url_path_map {
    name                               = "portal-routes"
    default_backend_address_pool_name  = "frontend"
    default_backend_http_settings_name = "frontend-https"

    path_rule {
      name                       = "api"
      paths                      = ["/api/*"]
      backend_address_pool_name  = "api"
      backend_http_settings_name = "api-https"
    }
  }

  redirect_configuration {
    name                 = "http-to-https"
    redirect_type        = "Permanent"
    target_listener_name = "https"
    include_path         = true
    include_query_string = true
  }

  request_routing_rule {
    name               = "https"
    rule_type          = "PathBasedRouting"
    http_listener_name = "https"
    url_path_map_name  = "portal-routes"
    priority           = 100
  }

  request_routing_rule {
    name                        = "http-redirect"
    rule_type                   = "Basic"
    http_listener_name          = "http"
    redirect_configuration_name = "http-to-https"
    priority                    = 110
  }

  lifecycle {
    precondition {
      condition     = trimspace(var.application_gateway_host_name) != "" && trimspace(var.application_gateway_certificate_secret_id) != ""
      error_message = "Application Gateway requires an approved DNS host name and a versionless Key Vault certificate secret ID."
    }
  }
}
