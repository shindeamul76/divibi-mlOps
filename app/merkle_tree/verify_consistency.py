import hashlib

# Define a class for each node in the Merkle Tree.
class MerkleNode:
    def __init__(self, content):
        self.left = None
        self.right = None
        self.content = content
        self.hash_value = compute_hash(content)

def compute_hash(data):
    """
    Compute the SHA-256 hash for a given data input.
    :param data: The data to hash.
    :return: The hash as a hexadecimal string.
    """
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def merge_hashes(hash1, hash2):
    """
    Combine two hash values into one by concatenating and hashing them.
    :param hash1: The first hash.
    :param hash2: The second hash.
    :return: The combined hash as a hexadecimal string.
    """
    return compute_hash(hash1 + hash2)

def construct_merkle_tree(leaves, file_writer=None):
    """
    Construct a Merkle Tree from the given list of leaves.
    :param leaves: A list of string values representing the leaves.
    :param file_writer: An optional file object to write the tree structure to.
    :return: The root node of the constructed Merkle Tree.
    """
    nodes = [MerkleNode(leaf) for leaf in leaves]

    while len(nodes) > 1:
        temp_nodes = []
        for i in range(0, len(nodes), 2):
            node_left = nodes[i]
            if i + 1 < len(nodes):
                node_right = nodes[i + 1]
            else:
                temp_nodes.append(nodes[i])
                break

            if file_writer:
                file_writer.write(f"Left Node: {node_left.content} | Hash: {node_left.hash_value}\n")
                file_writer.write(f"Right Node: {node_right.content} | Hash: {node_right.hash_value}\n")

            parent_content = node_left.hash_value + node_right.hash_value
            parent_node = MerkleNode(parent_content)
            parent_node.left = node_left
            parent_node.right = node_right

            if file_writer:
                file_writer.write(f"Parent (combination): {parent_node.content} | Hash: {parent_node.hash_value}\n")

            temp_nodes.append(parent_node)

        nodes = temp_nodes

    return nodes[0]

def validate_consistency(leaf_set1, leaf_set2):
    """
    Validate the consistency between two Merkle Trees derived from different sets of leaves.
    :param leaf_set1: The first list of leaves.
    :param leaf_set2: The second list of leaves.
    :return: A list of hash values demonstrating the consistency between the two trees.
    """
    common_length = 0
    while common_length < len(leaf_set1):
        if leaf_set1[common_length] != leaf_set2[common_length]:
            break
        common_length += 1
    
    if common_length < len(leaf_set1):
        return []

    root1 = construct_merkle_tree(leaf_set1)
    root2 = construct_merkle_tree(leaf_set2)
    consistency_proof = [root1.hash_value]

    if root1.hash_value == root2.hash_value:
        consistency_proof.append(root2.hash_value)
        return consistency_proof

    combined_root = merge_hashes(root1.hash_value, root2.hash_value)
    if combined_root == root2.hash_value:
        consistency_proof.extend([combined_root, root2.hash_value])
        return consistency_proof

    return []

def verify_inclusion(leaf, tree_root, leaf_set):
    """
    Verify that a specific leaf is included in the Merkle Tree.
    :param leaf: The leaf to verify.
    :param tree_root: The root hash of the Merkle Tree.
    :param leaf_set: The set of leaves to reconstruct the tree.
    :return: A list of hash values representing the path of inclusion.
    """
    inclusion_path = []
    nodes = [MerkleNode(l) for l in leaf_set]

    while len(nodes) > 1:
        temp_nodes = []
        for i in range(0, len(nodes), 2):
            node_left = nodes[i]
            if i + 1 < len(nodes):
                node_right = nodes[i + 1]
            else:
                temp_nodes.append(nodes[i])
                break

            if leaf in (node_left.content, node_right.content):
                sibling_node = node_right if leaf == node_left.content else node_left
                inclusion_path.append(sibling_node.hash_value)

            parent_content = node_left.hash_value + node_right.hash_value
            parent_node = MerkleNode(parent_content)
            parent_node.left = node_left
            parent_node.right = node_right
            temp_nodes.append(parent_node)

        nodes = temp_nodes

    return inclusion_path if nodes[0].hash_value == tree_root else []

