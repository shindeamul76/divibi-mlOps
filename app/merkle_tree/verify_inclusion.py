# verify_inclusion.py
import hashlib
import sys

def parse_merkle_tree(file_path="merkle.tree"):
    """
    Parse the Merkle tree structure from a file and return it as a dictionary.
    :param file_path: Path to the Merkle tree file.
    :return: Dictionary representing the Merkle tree.
    """
    merkle_tree = {}
    try:
        with open(file_path, "r") as f:
            for line in f:
                line_elements = line.split(" ")
                if line_elements[0] == 'Parent(concatenation':
                    parent_key = line_elements[6]
                    parent_hash = line_elements[10]
                    merkle_tree[parent_key] = parent_hash.strip()
                else:
                    node_key = line_elements[3]
                    node_hash = line_elements[7]
                    merkle_tree[node_key] = node_hash.strip()
    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
    except Exception as e:
        print(f"Error parsing the Merkle tree file: {e}")
    return merkle_tree

def check_inclusion_proof(input_value, tree_structure):
    """
    Check if a given input value is included in the Merkle tree.
    :param input_value: The value to check for inclusion.
    :param tree_structure: Dictionary representing the Merkle tree.
    :return: List of hashes proving the inclusion of the input value.
    """
    inclusion_path = []
    for key, value in tree_structure.items():
        if input_value in key:
            inclusion_path.append(value)
            input_value = value
    return inclusion_path

def main():
    """
    Main function to check inclusion in the Merkle tree.
    """
    if len(sys.argv) != 2:
        print("Usage: python verify_inclusion.py <input_string>")
        sys.exit(1)
    
    input_string = sys.argv[1]
    tree_structure = parse_merkle_tree()

    inclusion_proof = check_inclusion_proof(input_string, tree_structure)
    if len(inclusion_proof) > 0:
        print("Yes", inclusion_proof)
    else:
        print("No")

if __name__ == "__main__":
    main()
