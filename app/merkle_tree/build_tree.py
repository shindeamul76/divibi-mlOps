
import hashlib

class MerkleTreeNode:
    def __init__(self, value):
        self.left = None
        self.right = None
        self.value = value
        self.hashValue = hashlib.sha256(value.encode('utf-8')).hexdigest()

def build_tree(leaves, output_file_path):
    """
    Build a Merkle Tree from a list of leaves and write the structure to a file.
    
    :param leaves: List of string leaves.
    :param output_file_path: Path to the file where the tree structure will be written.
    :return: The root node of the Merkle Tree.
    """
    nodes = [MerkleTreeNode(leaf) for leaf in leaves]

    with open(output_file_path, "w") as f:
        while len(nodes) != 1:
            temp = []
            for i in range(0, len(nodes), 2):
                node1 = nodes[i]
                if i + 1 < len(nodes):
                    node2 = nodes[i + 1]
                else:
                    temp.append(nodes[i])
                    break
                f.write(f"Left child: {node1.value} | Hash: {node1.hashValue}\n")
                f.write(f"Right child: {node2.value} | Hash: {node2.hashValue}\n")
                concatenated_hash = node1.hashValue + node2.hashValue
                parent = MerkleTreeNode(concatenated_hash)
                parent.left = node1
                parent.right = node2
                f.write(f"Parent (concatenation of {node1.value} and {node2.value}): {parent.value} | Hash: {parent.hashValue}\n")
                temp.append(parent)
            nodes = temp
    return nodes[0]
