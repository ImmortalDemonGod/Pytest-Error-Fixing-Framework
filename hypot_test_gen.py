import logging
from pathlib import Path
import importlib.util
import sys
import subprocess
import ast
from typing import List, Tuple, Dict, Optional, Set, Union
from dataclasses import dataclass
import snoop
import os
import time

# Set up logging with file and console output
log_file = "test_generator_debug.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure snoop to write to a separate debug log
snoop.install(out=Path("snoop_debug.log"))

@dataclass
class TestableEntity:
    """Represents a class, method, or function that can be tested"""
    name: str
    module_path: str
    entity_type: str  # 'class', 'method', or 'function'
    parent_class: Optional[str] = None

def fix_pythonpath(file_path: Path) -> None:
    """Ensure the module being tested is in Python's path"""
    # Add parent directory to path if it's a single file
    parent_dir = str(file_path.parent.absolute())
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
        logger.debug(f"Added parent directory to sys.path: {parent_dir}")
        
    # Add src directory to path if it exists
    if 'src' in file_path.parts:
        src_index = file_path.parts.index('src')
        src_path = str(Path(*file_path.parts[:src_index+1]).absolute())
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
            logger.debug(f"Added src directory to sys.path: {src_path}")

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

@snoop
def debug_command_output(cmd: str, stdout: str, stderr: str, returncode: int) -> None:
    """Helper function to debug command execution"""
    logger.debug("Command execution details:")
    logger.debug(f"Command: {cmd}")
    logger.debug(f"Return code: {returncode}")
    logger.debug(f"stdout length: {len(stdout)}")
    logger.debug(f"stderr length: {len(stderr)}")
    logger.debug("First 1000 chars of stdout:")
    logger.debug(stdout[:1000])
    logger.debug("First 1000 chars of stderr:")
    logger.debug(stderr[:1000])

class TestGenerator:
    """Manages generation of Hypothesis tests for Python modules"""
    
    @snoop
    def __init__(self, output_dir: Path = Path("generated_tests")):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        logger.debug(f"Test generator initialized with output dir: {output_dir}")
        logger.debug(f"Output dir exists: {output_dir.exists()}")
        logger.debug(f"Output dir is writable: {os.access(output_dir, os.W_OK)}")
        
    @snoop
    def run_hypothesis_write(self, command: str) -> Optional[str]:
        """Execute hypothesis write command and return output if successful"""
        full_cmd = f"hypothesis write {command}"
        logger.debug(f"Executing hypothesis command: {full_cmd}")
        
        try:
            logger.debug(f"PYTHONPATH before modification: {os.getenv('PYTHONPATH')}")
            logger.debug(f"sys.path: {sys.path}")
            
            logger.debug(f"Current working directory: {os.getcwd()}")
            env = os.environ.copy()
            env['PYTHONPATH'] = ':'.join(sys.path)
            if 'PYTHONIOENCODING' not in env:
                env['PYTHONIOENCODING'] = 'utf-8'

            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True,
                env=env
            )
            
            debug_command_output(full_cmd, result.stdout, result.stderr, result.returncode)
            
            if result.returncode == 0 and result.stdout:
                content = result.stdout.strip()
                if not content or len(content) < 50:
                    logger.warning("Hypothesis generated insufficient content")
                    return None
                logger.info("Successfully generated test content")
                return content
            
            if result.stderr:
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

    @snoop
    def try_generate_test(self, entity: TestableEntity, variant: Dict[str, str], max_retries: int = 3) -> bool:
        """Attempt to generate a specific test variant with retries"""
        for attempt in range(max_retries):
            logger.debug(f"Attempt {attempt+1} for {variant['type']} test on {entity.name}")
            try:
                output = self.run_hypothesis_write(variant['cmd'])
                if output:
                    name_prefix = f"{entity.parent_class}_{entity.name}" if entity.parent_class else entity.name
                    output_file = self.output_dir / f"test_{name_prefix}_{variant['type']}.py"
                    
                    try:
                        logger.debug("Test content details:")
                        logger.debug(f"Content length: {len(output)}")
                        logger.debug(f"Content preview:\n{output[:1000]}")
                        logger.debug(f"Writing to file: {output_file}")
                        
                        output_file.write_text(output)
                        
                        # Verify written content
                        written_content = output_file.read_text()
                        if not written_content:
                            logger.error(f"File {output_file} is empty after writing!")
                            return False
                        
                        if written_content != output:
                            logger.error("Written content doesn't match original content!")
                            logger.debug(f"Original length: {len(output)}")
                            logger.debug(f"Written length: {len(written_content)}")
                            return False
                        
                        logger.info(f"Successfully generated test at {output_file}")
                        logger.debug(f"Final file size: {output_file.stat().st_size} bytes")
                        print(f"Generated {variant['type']} test: {output_file}")
                        return True
                        
                    except Exception as e:
                        logger.error(f"Error writing test file: {e}", exc_info=True)
                        logger.debug(f"Output file path: {output_file}")
                        logger.debug(f"Output content length: {len(output) if output else 0}")
                        return False
                else:
                    logger.warning("No output generated from hypothesis")
                    if attempt < max_retries - 1:
                        logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                        time.sleep(1)
                    else:
                        logger.error(f"All attempts failed for {entity.name}")
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed with error: {e}, retrying...")
                    time.sleep(1)
                else:
                    logger.error(f"All attempts failed for {entity.name}: {e}")
        return False

    def get_module_contents(self, file_path: Path) -> Tuple[str, List[TestableEntity]]:
        """Extract module path and testable entities using AST parsing"""
        logger.debug(f"Reading file: {file_path}")
        
        try:
            parts = file_path.parts
            if 'src' in parts:
                src_index = parts.index('src')
                module_parts = parts[src_index+1:]
            else:
                module_parts = [file_path.stem]
            
            module_path = '.'.join([p.replace('.py', '') for p in module_parts])
            logger.debug(f"Constructed module path: {module_path}")
            
            content = file_path.read_text()
            tree = ast.parse(content)
            parser = ModuleParser()
            parser.visit(tree)
            
            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.add(name.name)
                elif isinstance(node, ast.ImportFrom):
                    imports.add(node.module)
            
            logger.debug(f"Found imports: {imports}")
            
            entities = []
            for entity in parser.entities:
                if entity.entity_type in {'method', 'instance_method'}:
                    entity.module_path = f"{module_path}.{entity.parent_class}"
                else:
                    entity.module_path = module_path
                entities.append(entity)
            
            classes = sum(1 for e in entities if e.entity_type == 'class')
            methods = sum(1 for e in entities if e.entity_type in {'method', 'instance_method'})
            functions = sum(1 for e in entities if e.entity_type == 'function')
            
            logger.info(f"Found {classes} classes, {methods} methods, and {functions} functions")
            return module_path, entities
            
        except Exception as e:
            logger.error(f"Error parsing module contents: {e}", exc_info=True)
            raise

    def generate_test_variants(self, entity: TestableEntity) -> List[Dict[str, str]]:
        """Generate all applicable test variants for an entity"""
        variants = []
        
        if entity.entity_type == 'class':
            variants.append({
                "type": "basic",
                "cmd": f"--style=unittest --annotate {entity.module_path}.{entity.name}"
            })
            
        elif entity.entity_type in {'method', 'instance_method'}:
            method_path = f"{entity.module_path}.{entity.name}"
            variants.extend([
                {"type": "basic", "cmd": f"--style=unittest --annotate {method_path}"},
                {"type": "errors", "cmd": f"--style=unittest --annotate --except ValueError --except TypeError {method_path}"}
            ])
            
            if entity.entity_type == 'instance_method':
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

    def generate_all_tests(self, file_path: Path) -> None:
        """Generate all possible test variants for a Python file"""
        logger.info(f"Generating tests for file: {file_path}")
        
        try:
            fix_pythonpath(file_path)
            
            module_path, entities = self.get_module_contents(file_path)
            
            print(f"\nProcessing module: {module_path}")
            print(f"Found {len([e for e in entities if e.entity_type == 'class'])} classes, "
                  f"{len([e for e in entities if e.entity_type in {'method', 'instance_method'}])} methods, and "
                  f"{len([e for e in entities if e.entity_type == 'function'])} functions")
            
            total_variants = sum(len(self.generate_test_variants(e)) for e in entities)
            current = 0
            
            for entity in entities:
                print(f"\nGenerating tests for: {module_path}.{entity.name}")
                
                variants = self.generate_test_variants(entity)
                for variant in variants:
                    current += 1
                    print(f"\rGenerating tests: [{current}/{total_variants}]", end="")
                    self.try_generate_test(entity, variant)
            print()
                    
        except Exception as e:
            logger.error("Test generation failed", exc_info=True)
            raise

def parse_args(args: Optional[list] = None) -> Path:
    """
    Parse command line arguments and validate file path.
    
    Args:
        args: Optional list of command line arguments. If None, uses sys.argv[1:]
        
    Returns:
        Path object for the input file
        
    Raises:
        ValueError: If arguments are invalid or file doesn't exist
    """
    if args is None:
        args = sys.argv[1:]
        
    if len(args) != 1:
        raise ValueError("Exactly one argument (path to Python file) required")
        
    file_path = Path(args[0])
    if not file_path.exists() or not file_path.is_file():
        raise ValueError(f"File does not exist or is not a file: {file_path}")
        
    return file_path

def run_test_generation(file_path: Union[str, Path]) -> bool:
    """
    Run the test generation process for a given file.
    
    Args:
        file_path: Path to the Python file to generate tests for
        
    Returns:
        bool: True if test generation was successful, False otherwise
        
    Raises:
        Exception: If test generation fails
    """
    try:
        if isinstance(file_path, str):
            file_path = Path(file_path)
            
        logger.info(f"Starting test generator for {file_path}")
        generator = TestGenerator()
        generator.generate_all_tests(file_path)
        return True
        
    except Exception as e:
        logger.error(f"Test generation failed: {e}", exc_info=True)
        return False

def main(args: Optional[list] = None) -> int:
    """
    Main entry point for the test generator script.
    
    Args:
        args: Optional list of command line arguments. If None, uses sys.argv[1:]
        
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    try:
        file_path = parse_args(args)
        success = run_test_generation(file_path)
        return 0 if success else 1
        
    except ValueError as e:
        print(f"Error: {e}")
        logger.error(f"Invalid arguments: {e}")
        print("Usage: python test_generator.py <path_to_python_file>")
        return 1
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        logger.error("Unexpected error during execution", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())