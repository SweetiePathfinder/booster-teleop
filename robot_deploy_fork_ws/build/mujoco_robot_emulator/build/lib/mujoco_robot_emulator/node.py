#!/usr/bin/env python3
"""Executable entry point for MuJoCo ROS2 nodes.

Automatically discovers and registers all node classes in this package.
All configuration is read from ROS2 parameters by each node class.
"""
import sys
import argparse
import rclpy
import inspect
import importlib
import pkgutil
from pathlib import Path
from rclpy.node import Node


def _register_node_classes():
    """Discover and register all node classes in this package.
    
    Returns:
        dict[str, type[Node]]: Mapping of exact class name to class, e.g., {'K1': K1, 'General': General}
    """
    node_classes: dict[str, type[Node]] = {}
    package_path = Path(__file__).parent
    package_name = package_path.name
    
    # Iterate through all modules in the package
    for importer, modname, ispkg in pkgutil.iter_modules([str(package_path)]):
        # Import the module using relative import
        module = importlib.import_module(f'.{modname}', package=package_name)
        
        # Find all classes in the module that are Node subclasses
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Check if it's a Node subclass and defined in this module (not imported)
            if (issubclass(obj, Node) and 
                obj is not Node and 
                obj.__module__ == module.__name__):
                
                # Use exact class name as key (case-sensitive)
                class_name = obj.__name__
                node_classes[class_name] = obj
    return node_classes


def main(args=None):
    """Entry point for running MuJoCo ROS2 nodes.
    
    Reads the 'type' argument to determine which node class to instantiate.
    Each node class reads its own ROS2 parameters directly.
    """
    # Register all available node classes first (before parsing args)
    node_registry = _register_node_classes()
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='MuJoCo ROS2 node launcher')
    parser.add_argument(
        '--type',
        type=str,
        required=True,
        choices=list(node_registry.keys()),
        help=f'Type of node to run. Available: {", ".join(sorted(node_registry.keys()))}'
    )
    
    # Parse known args to allow ROS2 arguments to pass through
    if args is None:
        known_args, unknown_args = parser.parse_known_args()
    else:
        known_args, unknown_args = parser.parse_known_args(args)
    
    node_type = known_args.type
    
    # Initialize ROS2 with full sys.argv so it can process --ros-args and parameters
    rclpy.init(args=sys.argv if args is None else args)
    
    # Get the node class from registry
    node_class = node_registry.get(node_type)
    if node_class is None:
        print(f"Error: Node type '{node_type}' not found in registry. Available: {', '.join(sorted(node_registry.keys()))}", file=sys.stderr)
        rclpy.shutdown()
        sys.exit(1)
    
    # Create and run the actual node (it will read its own parameters)
    try:
        node = node_class()
        node.get_logger().info(f'Starting {node_type} MuJoCo node ({node_class.__name__})')
        
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down...')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
