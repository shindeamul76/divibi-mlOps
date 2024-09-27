
import chardet
from .build_tree import build_tree

def detect_encoding(file_path):
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read())
        return result['encoding']

def read_leaves_from_file(input_file_path):
    """
    Read the list of leaves from an input file with detected encoding.
    
    :param input_file_path: Path to the input file containing leaves.
    :return: List of leaves.
    """
    encoding = detect_encoding(input_file_path)
    print(f"Detected encoding: {encoding}")  # Debugging: Print the detected encoding

    try:
        # Attempt to read the file with the detected encoding
        with open(input_file_path, "r", encoding=encoding) as f:
            content = f.read().strip()
    except UnicodeDecodeError:
        print(f"Failed to read with detected encoding {encoding}. Retrying with 'utf-8' encoding...")
        # If detected encoding fails, fallback to 'utf-8' and ignore errors
        with open(input_file_path, "r", encoding="utf-8", errors='ignore') as f:
            content = f.read().strip()
    except Exception as e:
        print(f"An unexpected error occurred while reading the file: {e}")
        raise e

    return content.split(',')




def write_tree_to_file(tree, output_file_path):
    """
    Write the Merkle Tree structure to a file.
    
    :param tree: The root node of the Merkle Tree.
    :param output_file_path: Path to the file where the tree structure will be written.
    """
    with open(output_file_path, "w") as f:
        _write_node(tree, f)

def _write_node(node, f):
    """
    Recursive helper function to write each node of the Merkle Tree to the file.
    
    :param node: The current node.
    :param f: File object to write to.
    """
    if node is None:
        return
    if node.left is not None and node.right is not None:
        f.write(f"Parent (concatenation of {node.left.value} and {node.right.value}): {node.value} | Hash: {node.hashValue}\n")
    _write_node(node.left, f)
    _write_node(node.right, f)


def verify_model_integrity(local_filename, stored_merkle_root):
    # Step 1: Read the contents of the downloaded file as leaves
    leaves = read_leaves_from_file(local_filename)

    # Step 2: Create a temporary file path for the Merkle Tree structure
    temp_merkle_file = f"{local_filename}_merkle.tree"

    # Step 3: Build the Merkle Tree and get the root
    root = build_tree(leaves, temp_merkle_file)

    # Step 4: Compare the generated Merkle root with the stored root
    if root.hashValue == stored_merkle_root:
        return True
    return False
