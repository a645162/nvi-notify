"""
global_system_info为一个Hashmap
包括:
物理内存、分页内存(总量/使用量/剩余量)
"""

global_system_info: dict = {
    "memory_physic_total_mb": 0,
    "memory_physic_used_mb": 0,
    "memory_physic_free_mb": 0,

    "memory_swap_total_mb": 0,
    "memory_swap_used_mb": 0,
    "memory_swap_free_mb": 0,
}
