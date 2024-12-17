import logging
from pathlib import Path
import importlib.util
import sys
import subprocess
import ast
from typing import List, Tuple, Dict, Optional, Set
from dataclasses import dataclass

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TestableEntity:
    """Represents a class, method, or function that can be tested"""
    name: str
    module_path: str
    entity_type: str  # 'class', 'method', or 'function'
    parent_class: Optional[str] = None
    
class ModuleParser(ast.NodeVisitor):
    """AST-based parser for Python modules"""
    
    def __init__(self):
        self.entities: List[TestableEntity] = []
        self.current_class: Optional[str] = None
        self.class_bases: Dict[str, List[str]] = {}
        
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if not node.name.startswith('_'):
            # Store base classes for inheritance checking
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(f"{base.value.id}.{base.attr}")
            self.class_bases[node.name] = bases
            
            # Add the class itself
            self.entities.append(TestableEntity(node.name, '', 'class'))
            
            # Process class contents
            old_class = self.current_class
            self.current_class = node.name
            self.generic_visit(node)
            self.current_class = old_class
            
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if not node.name.startswith('_'):
            if self.current_class:
                # Check if this is an instance method that needs an instance
                is_instance_method = False
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id in {'classmethod', 'staticmethod'}:
                        is_instance_method = False
                        break
                    is_instance_method = True
                
                # Skip methods that are likely inherited/bound
                current_bases = self.class_bases.get(self.current_class, [])
                if any(base in {'NodeVisitor', 'ast.NodeVisitor'} for base in current_bases):
                    if node.name.startswith('visit_'):
                        return
                
                # Skip common magic methods and property methods
                if node.name not in {'__init__', '__str__', '__repr__', 'property'}:
                    self.entities.append(TestableEntity(
                        node.name,
                        '',
                        'instance_method' if is_instance_method else 'method',
                        self.current_class
                    ))
            else:
                self.entities.append(TestableEntity(node.name, '', 'function'))
                
class TestGenerator:
    """Manages generation of Hypothesis tests for Python modules"""
    
    def __init__(self, output_dir: Path = Path("generated_tests")):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        
    def get_module_contents(self, file_path: Path) -> Tuple[str, List[TestableEntity]]:
        """Extract module path and testable entities using AST parsing"""
        logger.debug(f"Reading file: {file_path}")
        
        try:
            # Get module path
            parts = file_path.parts
            if 'src' in parts:
                src_index = parts.index('src')
                module_parts = parts[src_index+1:]
            else:
                module_parts = [file_path.stem]
            
            module_path = '.'.join([p.replace('.py', '') for p in module_parts])
            logger.debug(f"Constructed module path: {module_path}")
            
            # Parse file using AST
            content = file_path.read_text()
            tree = ast.parse(content)
            parser = ModuleParser()
            parser.visit(tree)
            
            # Update module paths
            entities = []
            for entity in parser.entities:
                if entity.entity_type == 'method':
                    # For methods, we need to generate tests through their class
                    entity.module_path = f"{module_path}.{entity.parent_class}"
                else:
                    entity.module_path = module_path
                entities.append(entity)
            
            # Log what we found
            classes = sum(1 for e in entities if e.entity_type == 'class')
            methods = sum(1 for e in entities if e.entity_type == 'method')
            functions = sum(1 for e in entities if e.entity_type == 'function')
            
            logger.info(f"Found {classes} classes, {methods} methods, and {functions} functions")
            return module_path, entities
            
        except Exception as e:
            logger.error(f"Error parsing module contents: {e}", exc_info=True)
            raise

    def run_hypothesis_write(self, command: str) -> Optional[str]:
        """Execute hypothesis write command and return output if successful"""
        full_cmd = f"hypothesis write {command}"
        logger.debug(f"Executing: {full_cmd}")
        
        try:
            result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout:
                logger.info("Successfully generated test")
                return result.stdout
            
            if result.stderr:
                # Skip logging for common expected errors
                if not any(msg in result.stderr for msg in [
                    "InvalidArgument: Got non-callable",
                    "Could not resolve",
                    "but it doesn't have a"
                ]):
                    logger.warning(f"Command failed: {result.stderr}")
            return None
            
        except Exception as e:
            logger.error(f"Error running hypothesis: {e}", exc_info=True)
            return None
    
    def generate_test_variants(self, entity: TestableEntity) -> List[Dict[str, str]]:
        """Generate all applicable test variants for an entity"""
        variants = []
        
        if entity.entity_type == 'class':
            # Basic test for the class
            variants.append({
                "type": "basic",
                "cmd": f"--style=unittest --annotate {entity.module_path}.{entity.name}"
            })
            
        elif entity.entity_type == 'method':
            # For regular methods (not instance methods)
            method_path = f"{entity.module_path}.{entity.name}"
            variants.extend([
                {"type": "basic", "cmd": f"--style=unittest --annotate {method_path}"},
                {"type": "errors", "cmd": f"--style=unittest --annotate --except ValueError,TypeError {method_path}"}
            ])
            
        elif entity.entity_type == 'instance_method':
            # For instance methods, we need to test through class instances
            # These need special handling in the generated test file
            method_path = f"{entity.module_path}.{entity.name}"
            variants.append({
                "type": "basic",
                "cmd": f"--style=unittest --annotate {method_path}"
            })
            
            # Add specific test types based on method name
            name = entity.name.lower()
            if any(x in name for x in ['validate', 'verify', 'check']):
                variants.append({
                    "type": "validation",
                    "cmd": f"--style=unittest --annotate --errors-equivalent {method_path}"
                })
            elif any(x in name for x in ['transform', 'convert', 'process']):
                variants.append({
                    "type": "idempotent",
                    "cmd": f"--style=unittest --annotate --idempotent {method_path}"
                })
            
        else:  # functions
            base_cmd = f"--style=unittest --annotate {entity.module_path}.{entity.name}"
            variants.append({"type": "basic", "cmd": base_cmd})
            
            if any(x in entity.name.lower() for x in ['encode', 'decode', 'serialize', 'deserialize']):
                variants.append({"type": "roundtrip", "cmd": f"{base_cmd} --roundtrip"})
            elif any(x in entity.name.lower() for x in ['add', 'sub', 'mul', 'combine', 'merge']):
                variants.append({"type": "binary-op", "cmd": f"{base_cmd} --binary-op"})
                
        return variants

    def try_generate_test(self, entity: TestableEntity, variant: Dict[str, str]) -> bool:
        """Attempt to generate a specific test variant"""
        logger.debug(f"Attempting {variant['type']} test for {entity.name}")
        
        output = self.run_hypothesis_write(variant['cmd'])
        if output:
            # For methods, include the class name in the filename
            name_prefix = f"{entity.parent_class}_{entity.name}" if entity.parent_class else entity.name
            output_file = self.output_dir / f"test_{name_prefix}_{variant['type']}.py"
            
            try:
                output_file.write_text(output)
                logger.info(f"Generated {variant['type']} test for {entity.name}")
                print(f"Generated {variant['type']} test: {output_file}")
                return True
            except Exception as e:
                logger.error(f"Error writing test file: {e}")
                return False
                
        return False

    def generate_all_tests(self, file_path: Path) -> None:
        """Generate all possible test variants for a Python file"""
        logger.info(f"Generating tests for file: {file_path}")
        
        try:
            module_path, entities = self.get_module_contents(file_path)
            
            print(f"\nProcessing module: {module_path}")
            print(f"Found {len([e for e in entities if e.entity_type == 'class'])} classes, "
                  f"{len([e for e in entities if e.entity_type == 'method'])} methods, and "
                  f"{len([e for e in entities if e.entity_type == 'function'])} functions")
            
            for entity in entities:
                print(f"\nGenerating tests for: {module_path}.{entity.name}")
                
                # Try generating each applicable test variant
                for variant in self.generate_test_variants(entity):
                    self.try_generate_test(entity, variant)
                    
        except Exception as e:
            logger.error("Test generation failed", exc_info=True)
            raise

def main():
    """Entry point for the test generator script"""
    if len(sys.argv) != 2:
        print("Usage: python test_generator.py <path_to_python_file>")
        sys.exit(1)
        
    file_path = Path(sys.argv[1])
    if not file_path.exists() or not file_path.is_file():
        print(f"Error: {file_path} does not exist or is not a file")
        sys.exit(1)
        
    generator = TestGenerator()
    generator.generate_all_tests(file_path)

if __name__ == "__main__":
    main()