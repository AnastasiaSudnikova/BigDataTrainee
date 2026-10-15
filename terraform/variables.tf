variable "project_id" {
  type    = string
  default = "weather-pipeline-anastasia"
}

variable "region" {
  type    = string
  default = "europe-west1"
}

variable "env" {
  type    = string
  default = "dev"
}

variable "weather_api_key" {
  type      = string
  sensitive = true
}