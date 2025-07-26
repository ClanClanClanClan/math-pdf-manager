#!/usr/bin/env python3
"""
API Documentation Generator
Automatically generates comprehensive API documentation
"""

import inspect
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass, field
import importlib
import pkgutil

logger = logging.getLogger(__name__)


@dataclass
class ParameterDoc:
    """Documentation for a function parameter."""
    name: str
    type_hint: Optional[str] = None
    default: Optional[str] = None
    description: Optional[str] = None
    required: bool = True


@dataclass
class FunctionDoc:
    """Documentation for a function."""
    name: str
    module: str
    signature: str
    docstring: Optional[str] = None
    parameters: List[ParameterDoc] = field(default_factory=list)
    returns: Optional[str] = None
    raises: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    is_async: bool = False
    line_number: Optional[int] = None


@dataclass
class ClassDoc:
    """Documentation for a class."""
    name: str
    module: str
    docstring: Optional[str] = None
    bases: List[str] = field(default_factory=list)
    methods: List[FunctionDoc] = field(default_factory=list)
    attributes: Dict[str, str] = field(default_factory=dict)
    line_number: Optional[int] = None


@dataclass
class ModuleDoc:
    """Documentation for a module."""
    name: str
    path: str
    docstring: Optional[str] = None
    classes: List[ClassDoc] = field(default_factory=list)
    functions: List[FunctionDoc] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    constants: Dict[str, Any] = field(default_factory=dict)


class DocstringParser:
    """Parse docstrings in various formats."""
    
    @staticmethod
    def parse_google_style(docstring: str) -> Dict[str, Any]:
        """Parse Google-style docstring."""
        if not docstring:
            return {}
        
        lines = docstring.strip().split('\n')
        result = {
            'summary': '',
            'description': '',
            'args': {},
            'returns': '',
            'raises': [],
            'examples': []
        }
        
        current_section = 'description'
        current_arg = None
        buffer = []
        
        for line in lines:
            stripped = line.strip()
            
            # Check for section headers
            if stripped in ['Args:', 'Arguments:', 'Parameters:']:
                current_section = 'args'
                continue
            elif stripped in ['Returns:', 'Return:']:
                current_section = 'returns'
                continue
            elif stripped in ['Raises:', 'Raise:']:
                current_section = 'raises'
                continue
            elif stripped in ['Example:', 'Examples:']:
                current_section = 'examples'
                continue
            elif stripped.startswith('>>>'):
                current_section = 'examples'
            
            # Process content based on section
            if current_section == 'description':
                if not result['summary'] and stripped:
                    result['summary'] = stripped
                elif stripped:
                    buffer.append(line)
            
            elif current_section == 'args' and stripped:
                # Check if it's a new parameter
                if ':' in line and not line.startswith('    '):
                    if current_arg and buffer:
                        result['args'][current_arg] = ' '.join(buffer).strip()
                        buffer = []
                    
                    parts = line.split(':', 1)
                    current_arg = parts[0].strip()
                    if len(parts) > 1:
                        buffer.append(parts[1])
                else:
                    buffer.append(line)
            
            elif current_section == 'returns':
                buffer.append(line)
            
            elif current_section == 'raises':
                if stripped and not line.startswith('    '):
                    result['raises'].append(stripped)
            
            elif current_section == 'examples':
                result['examples'].append(line)
        
        # Process remaining buffer
        if current_section == 'args' and current_arg and buffer:
            result['args'][current_arg] = ' '.join(buffer).strip()
        elif current_section == 'returns' and buffer:
            result['returns'] = ' '.join(buffer).strip()
        elif current_section == 'description' and buffer:
            result['description'] = '\n'.join(buffer).strip()
        
        return result


class APIDocGenerator:
    """Generate comprehensive API documentation."""
    
    def __init__(self, base_path: Optional[Path] = None):
        self.parser = DocstringParser()
        self.base_path = base_path or Path.cwd()
    
    def extract_function_doc(self, func: Any, module_name: str) -> FunctionDoc:
        """Extract documentation from a function."""
        # Get signature
        try:
            sig = inspect.signature(func)
            signature = str(sig)
        except Exception:
            signature = "(...)"
        
        # Parse docstring
        docstring = inspect.getdoc(func)
        parsed_doc = self.parser.parse_google_style(docstring) if docstring else {}
        
        # Extract parameters
        parameters = []
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            param_doc = ParameterDoc(
                name=param_name,
                type_hint=str(param.annotation) if param.annotation != param.empty else None,
                default=str(param.default) if param.default != param.empty else None,
                required=param.default == param.empty,
                description=parsed_doc.get('args', {}).get(param_name)
            )
            parameters.append(param_doc)
        
        # Get decorators
        decorators = []
        if hasattr(func, '__wrapped__'):
            # Function has decorators
            decorators.append('@decorated')
        
        return FunctionDoc(
            name=func.__name__,
            module=module_name,
            signature=signature,
            docstring=parsed_doc.get('summary', ''),
            parameters=parameters,
            returns=parsed_doc.get('returns'),
            raises=parsed_doc.get('raises', []),
            examples=parsed_doc.get('examples', []),
            decorators=decorators,
            is_async=inspect.iscoroutinefunction(func)
        )
    
    def extract_class_doc(self, cls: Type, module_name: str) -> ClassDoc:
        """Extract documentation from a class."""
        # Get base classes
        bases = [base.__name__ for base in cls.__bases__ if base.__name__ != 'object']
        
        # Get docstring
        docstring = inspect.getdoc(cls)
        
        # Extract methods
        methods = []
        for name, method in inspect.getmembers(cls, inspect.isfunction):
            if not name.startswith('_') or name in ['__init__', '__str__', '__repr__']:
                method_doc = self.extract_function_doc(method, module_name)
                methods.append(method_doc)
        
        # Extract class attributes
        attributes = {}
        for name, value in cls.__dict__.items():
            if not name.startswith('_') and not callable(value):
                attributes[name] = str(type(value).__name__)
        
        return ClassDoc(
            name=cls.__name__,
            module=module_name,
            docstring=docstring,
            bases=bases,
            methods=methods,
            attributes=attributes
        )
    
    def extract_module_doc(self, module: Any) -> ModuleDoc:
        """Extract documentation from a module."""
        module_name = module.__name__
        module_path = getattr(module, '__file__', 'unknown')
        
        # Get module docstring
        docstring = inspect.getdoc(module)
        
        # Extract classes
        classes = []
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ == module_name:
                class_doc = self.extract_class_doc(obj, module_name)
                classes.append(class_doc)
        
        # Extract functions
        functions = []
        for name, obj in inspect.getmembers(module, inspect.isfunction):
            if obj.__module__ == module_name:
                func_doc = self.extract_function_doc(obj, module_name)
                functions.append(func_doc)
        
        # Extract constants
        constants = {}
        for name, value in module.__dict__.items():
            if name.isupper() and not callable(value):
                constants[name] = repr(value)
        
        return ModuleDoc(
            name=module_name,
            path=module_path,
            docstring=docstring,
            classes=classes,
            functions=functions,
            constants=constants
        )
    
    def generate_markdown(self, module_doc: ModuleDoc) -> str:
        """Generate Markdown documentation for a module."""
        lines = []
        
        # Module header
        lines.append(f"# {module_doc.name}")
        lines.append("")
        
        if module_doc.docstring:
            lines.append(module_doc.docstring)
            lines.append("")
        
        # Constants
        if module_doc.constants:
            lines.append("## Constants")
            lines.append("")
            for name, value in module_doc.constants.items():
                lines.append(f"- `{name}`: {value}")
            lines.append("")
        
        # Functions
        if module_doc.functions:
            lines.append("## Functions")
            lines.append("")
            
            for func in module_doc.functions:
                lines.append(f"### {func.name}")
                lines.append("")
                lines.append("```python")
                lines.append(f"{'async ' if func.is_async else ''}def {func.name}{func.signature}")
                lines.append("```")
                lines.append("")
                
                if func.docstring:
                    lines.append(func.docstring)
                    lines.append("")
                
                if func.parameters:
                    lines.append("**Parameters:**")
                    lines.append("")
                    for param in func.parameters:
                        req = "" if param.required else " (optional)"
                        type_info = f": {param.type_hint}" if param.type_hint else ""
                        default = f" = {param.default}" if param.default else ""
                        desc = f" - {param.description}" if param.description else ""
                        lines.append(f"- `{param.name}{type_info}{default}`{req}{desc}")
                    lines.append("")
                
                if func.returns:
                    lines.append("**Returns:**")
                    lines.append("")
                    lines.append(func.returns)
                    lines.append("")
                
                if func.raises:
                    lines.append("**Raises:**")
                    lines.append("")
                    for exc in func.raises:
                        lines.append(f"- {exc}")
                    lines.append("")
        
        # Classes
        if module_doc.classes:
            lines.append("## Classes")
            lines.append("")
            
            for cls in module_doc.classes:
                lines.append(f"### {cls.name}")
                
                if cls.bases:
                    lines.append(f"*Inherits from: {', '.join(cls.bases)}*")
                
                lines.append("")
                
                if cls.docstring:
                    lines.append(cls.docstring)
                    lines.append("")
                
                if cls.attributes:
                    lines.append("**Attributes:**")
                    lines.append("")
                    for name, type_name in cls.attributes.items():
                        lines.append(f"- `{name}`: {type_name}")
                    lines.append("")
                
                if cls.methods:
                    lines.append("**Methods:**")
                    lines.append("")
                    
                    for method in cls.methods:
                        lines.append(f"#### {method.name}")
                        lines.append("")
                        lines.append("```python")
                        lines.append(f"{method.name}{method.signature}")
                        lines.append("```")
                        lines.append("")
                        
                        if method.docstring:
                            lines.append(method.docstring)
                            lines.append("")
        
        return '\n'.join(lines)
    
    def generate_docs_for_package(self, package_path: Path) -> Dict[str, str]:
        """Generate documentation for all modules in a package."""
        docs = {}
        
        # Import the package
        package_name = package_path.name
        spec = importlib.util.spec_from_file_location(
            package_name, 
            package_path / "__init__.py"
        )
        
        if spec and spec.loader:
            package = importlib.util.module_from_spec(spec)
            # SECURITY: Only load trusted internal modules - validate package path
            if not str(package_path).startswith(str(self.base_path)):
                logger.warning(f"Skipping untrusted package path: {package_path}")
                return docs
            spec.loader.exec_module(package)
            
            # Walk through all modules
            for importer, modname, ispkg in pkgutil.walk_packages(
                [str(package_path)], 
                f"{package_name}."
            ):
                try:
                    module = importlib.import_module(modname)
                    module_doc = self.extract_module_doc(module)
                    markdown = self.generate_markdown(module_doc)
                    docs[modname] = markdown
                except Exception as e:
                    docs[modname] = f"Error generating docs: {str(e)}"
        
        return docs