import logging
import os
from typing import List, Dict, Any, Optional
import tree_sitter
import tree_sitter_java
from ingestion.base_adapter import BaseAdapter, IngestedChunk
from rag.chunking import chunk_for_code

logger = logging.getLogger("karate_ai")

class SourceCodeAdapter(BaseAdapter):
    def __init__(self):
        # Initialize tree-sitter with Java grammar (using >=0.22 API)
        self.language = tree_sitter.Language(tree_sitter_java.language())
        self.parser = tree_sitter.Parser(self.language)
        
    def _get_node_text(self, node, source_bytes: bytes) -> str:
        if node is None:
            return ""
        return source_bytes[node.start_byte:node.end_byte].decode('utf-8')

    def ingest(self, source_path: str) -> List[IngestedChunk]:
        """
        Ingests all .java files in the given directory or file path.
        """
        chunks = []
        
        if os.path.isfile(source_path):
            if source_path.endswith(".java"):
                chunks.extend(self._parse_java_file(source_path))
        elif os.path.isdir(source_path):
            for root, _, files in os.walk(source_path):
                for file in files:
                    if file.endswith(".java"):
                        full_path = os.path.join(root, file)
                        chunks.extend(self._parse_java_file(full_path))
        else:
            logger.warning(f"Source path {source_path} is neither a file nor a directory.")
            
        logger.info(f"Extracted {len(chunks)} methods from Java source code")
        return chunks

    def _parse_java_file(self, file_path: str) -> List[IngestedChunk]:
        try:
            with open(file_path, "rb") as f:
                source_bytes = f.read()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return []

        tree = self.parser.parse(source_bytes)
        root_node = tree.root_node
        
        # Find all class declarations
        class_nodes = self._find_nodes_by_type(root_node, "class_declaration")
        
        chunks = []
        
        for class_node in class_nodes:
            class_info = self._extract_class_info(class_node, source_bytes)
            
            # Find methods inside the class body
            class_body = self._get_child_by_type(class_node, "class_body")
            if not class_body:
                continue
                
            method_nodes = self._find_nodes_by_type(class_body, "method_declaration")
            
            for method_node in method_nodes:
                method_info = self._extract_method_info(method_node, source_bytes)
                if not method_info:
                    continue
                    
                # Determine endpoint tag
                endpoint_tag = self._determine_endpoint_tag(class_info, method_info)
                if not endpoint_tag:
                    endpoint_tag = f"Method: {class_info['name']}.{method_info['name']}"
                    mapping_confidence = "low"
                else:
                    mapping_confidence = "high"
                    
                content = chunk_for_code(class_info, method_info)
                
                chunk = IngestedChunk(
                    content=content,
                    origin_type="code",
                    source_file=file_path,
                    endpoint_tag=endpoint_tag,
                    chunk_type="service_method",
                    metadata={
                        "class_name": class_info['name'],
                        "method_name": method_info['name'],
                        "mapping_confidence": mapping_confidence,
                        "language": "java"
                    }
                )
                chunks.append(chunk)
                
        return chunks

    def _extract_class_info(self, class_node, source_bytes: bytes) -> Dict[str, Any]:
        name_node = self._get_child_by_type(class_node, "identifier")
        name = self._get_node_text(name_node, source_bytes)
        
        # Extract annotations
        annotations = []
        modifiers = self._get_child_by_type(class_node, "modifiers")
        if modifiers:
            for child in modifiers.children:
                if child.type == "marker_annotation" or child.type == "annotation":
                    annotations.append(self._get_node_text(child, source_bytes))
                    
        return {
            "name": name,
            "annotations": annotations
        }

    def _extract_method_info(self, method_node, source_bytes: bytes) -> Optional[Dict[str, Any]]:
        name_node = self._get_child_by_type(method_node, "identifier")
        if not name_node:
            return None
            
        name = self._get_node_text(name_node, source_bytes)
        body_node = self._get_child_by_type(method_node, "block")
        if not body_node:
            # abstract method or interface method
            body = ""
        else:
            body = self._get_node_text(body_node, source_bytes)
            
        # Extract annotations
        annotations = []
        modifiers = self._get_child_by_type(method_node, "modifiers")
        if modifiers:
            for child in modifiers.children:
                if child.type == "marker_annotation" or child.type == "annotation":
                    annotations.append(self._get_node_text(child, source_bytes))
                    
        # Return type
        type_node = self._get_child_by_type(method_node, "type_identifier")
        if not type_node:
             # Try primitive type
             for child in method_node.children:
                 if "type" in child.type:
                     type_node = child
                     break
                     
        return_type = self._get_node_text(type_node, source_bytes) if type_node else "void"
        
        # Parameters
        parameters = []
        params_node = self._get_child_by_type(method_node, "formal_parameters")
        if params_node:
            for child in params_node.children:
                if child.type == "formal_parameter":
                    parameters.append(self._get_node_text(child, source_bytes))

        return {
            "name": name,
            "annotations": annotations,
            "return_type": return_type,
            "parameters": parameters,
            "body": body
        }

    def _determine_endpoint_tag(self, class_info: Dict[str, Any], method_info: Dict[str, Any]) -> str:
        """
        Attempts to map Spring Boot annotations to an OpenAPI endpoint tag.
        E.g. @PostMapping("/orders") -> "POST /orders"
        """
        base_path = ""
        # Check class level @RequestMapping
        for ann in class_info.get("annotations", []):
            if "RequestMapping" in ann:
                # Naive parsing to extract path: @RequestMapping("/api/v1/orders")
                import re
                match = re.search(r'\"([^\"]+)\"', ann)
                if match:
                    base_path = match.group(1)
                    
        # Check method level annotations
        for ann in method_info.get("annotations", []):
            method = None
            if "GetMapping" in ann: method = "GET"
            elif "PostMapping" in ann: method = "POST"
            elif "PutMapping" in ann: method = "PUT"
            elif "DeleteMapping" in ann: method = "DELETE"
            elif "PatchMapping" in ann: method = "PATCH"
            
            if method:
                import re
                path = ""
                match = re.search(r'\"([^\"]+)\"', ann)
                if match:
                    path = match.group(1)
                
                # Combine base_path and path, removing duplicate slashes
                full_path = f"{base_path}{path}".replace("//", "/")
                # For endpoints like /orders/{id}, ensure exact match with spec by not replacing placeholders
                
                if full_path:
                    return f"{method} {full_path}"
                return f"{method} {base_path}"
                
        return ""

    def _find_nodes_by_type(self, node, node_type: str) -> List[Any]:
        nodes = []
        if node.type == node_type:
            nodes.append(node)
        for child in node.children:
            nodes.extend(self._find_nodes_by_type(child, node_type))
        return nodes
        
    def _get_child_by_type(self, node, node_type: str):
        for child in node.children:
            if child.type == node_type:
                return child
        return None
