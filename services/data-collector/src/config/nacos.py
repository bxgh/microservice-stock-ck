import logging
from v2.nacos import ClientConfigBuilder, NacosNamingService, RegisterInstanceParam
from config.settings import settings

logger = logging.getLogger("data-collector.nacos")

class NacosManager:
    """Nacos 服务注册管理器"""
    
    def __init__(self):
        self.naming_service = None
        self.service_name = settings.name
        self.host = settings.host
        self.port = settings.port
        self.server_addr = settings.nacos_server
        self.namespace = settings.nacos_namespace

    def register(self):
        """注册服务到 Nacos"""
        try:
            logger.info(f"正在注册服务 {self.service_name} 到 Nacos ({self.server_addr})...")
            # 处理可能的协议前缀
            server_addr = self.server_addr.replace("http://", "").replace("https://", "")
            
            # 使用 nacos-sdk-python 3.x API - 直接使用 ClientConfig 支持 namespace
            from v2.nacos import ClientConfig
            
            client_config = ClientConfig(
                server_addresses=[server_addr],
                namespace=self.namespace if self.namespace else ""
            )
            
            self.naming_service = NacosNamingService(client_config)
            
            register_param = RegisterInstanceParam(
                service_name=self.service_name,
                ip=self.host,
                port=self.port,
                cluster_name="DEFAULT",
                metadata={
                    "version": settings.version,
                    "type": "fastapi",
                    "description": "Data Collector Service"
                }
            )
            
            self.naming_service.register_instance(register_param)
            logger.info(f"✅ 服务 {self.service_name} 注册成功: {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"❌ Nacos 注册失败: {e}")
            return False

    def unregister(self):
        """从 Nacos 注销服务"""
        if self.naming_service:
            try:
                logger.info(f"正在从 Nacos 注销服务 {self.service_name}...")
                # nacos-sdk-python 3.x 的注销方式
                from v2.nacos import DeregisterInstanceParam
                
                deregister_param = DeregisterInstanceParam(
                    service_name=self.service_name,
                    ip=self.host,
                    port=self.port
                )
                
                self.naming_service.deregister_instance(deregister_param)
                logger.info(f"✅ 服务 {self.service_name} 已注销")
                return True
            except Exception as e:
                logger.error(f"❌ Nacos 注销失败: {e}")
                return False
        return True

nacos_manager = NacosManager()

async def register_to_nacos():
    """便捷函数: 注册"""
    return nacos_manager.register()

async def unregister_from_nacos():
    """便捷函数: 注销"""
    return nacos_manager.unregister()
