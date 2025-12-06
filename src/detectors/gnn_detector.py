"""GNN-based anomaly detector using graph embeddings."""
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, lit, when, monotonically_increasing_id
from pyspark.sql.types import DoubleType, BooleanType, StringType
from typing import List, Dict, Optional
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# Try importing PyTorch Geometric
try:
    import torch
    import torch.nn as nn
    from torch_geometric.nn import SAGEConv, GATConv
    from torch_geometric.data import Data
    PYG_AVAILABLE = True
except ImportError:
    PYG_AVAILABLE = False
    print("Warning: PyTorch Geometric not available. Using node2vec fallback.")

# Try importing node2vec
try:
    import networkx as nx
    from node2vec import Node2Vec
    NODE2VEC_AVAILABLE = True
except ImportError:
    try:
        import networkx as nx
        NODE2VEC_AVAILABLE = False
        print("Warning: node2vec not available. Using simple DeepWalk-style embedding.")
    except ImportError:
        nx = None
        NODE2VEC_AVAILABLE = False
        print("Warning: networkx not available. GNN detector will be disabled.")


class GNNDetector:
    """Detect anomalies using graph neural networks or graph embeddings."""
    
    def __init__(
        self,
        spark: SparkSession,
        method: str = 'auto',  # 'gnn', 'node2vec', 'deepwalk', 'auto'
        score_percentile: float = 95.0,
        max_edges_for_graph: int = 10000,
        embedding_dim: int = 64,
        n_clusters: int = 50
    ):
        """
        Initialize GNN detector.
        
        Args:
            spark: SparkSession
            method: Method to use ('auto' tries GNN first, then node2vec, then simple)
            score_percentile: Percentile threshold for anomaly flagging
            max_edges_for_graph: Maximum edges to include in graph (for performance)
            embedding_dim: Dimension of node embeddings
            n_clusters: Number of clusters for anomaly detection
        """
        self.spark = spark
        self.method = method
        self.score_percentile = score_percentile
        self.max_edges_for_graph = max_edges_for_graph
        self.embedding_dim = embedding_dim
        self.n_clusters = n_clusters
        
        # Determine which method to use
        if method == 'auto':
            if PYG_AVAILABLE:
                self.method = 'gnn'
            elif NODE2VEC_AVAILABLE:
                self.method = 'node2vec'
            elif nx is not None:
                self.method = 'deepwalk'
            else:
                self.method = 'none'
                print("Warning: No graph libraries available. GNN detector disabled.")
        else:
            self.method = method
    
    def build_graph(self, df: DataFrame) -> Optional[object]:
        """
        Build graph from edge data.
        
        Args:
            df: DataFrame with prev, curr, n columns
            
        Returns:
            NetworkX graph or PyG Data object
        """
        # Sample top edges if too many
        edge_counts = df.groupBy("prev", "curr").sum("n").alias("weight")
        edge_counts = edge_counts.orderBy(col("sum(n)").desc()).limit(self.max_edges_for_graph)
        
        # Convert to pandas for graph building
        edges_pdf = edge_counts.toPandas()
        
        if len(edges_pdf) == 0:
            return None
        
        if self.method == 'gnn' and PYG_AVAILABLE:
            return self._build_pyg_graph(edges_pdf)
        elif nx is not None:
            return self._build_nx_graph(edges_pdf)
        else:
            return None
    
    def _build_pyg_graph(self, edges_pdf: pd.DataFrame):
        """Build PyTorch Geometric graph."""
        import torch
        from torch_geometric.data import Data
        
        # Create node mapping
        all_nodes = set(edges_pdf['prev'].unique()) | set(edges_pdf['curr'].unique())
        node_to_idx = {node: idx for idx, node in enumerate(all_nodes)}
        
        # Create edge index
        edge_index = []
        edge_weights = []
        
        for _, row in edges_pdf.iterrows():
            src = node_to_idx[row['prev']]
            dst = node_to_idx[row['curr']]
            weight = float(row['sum(n)'])
            edge_index.append([src, dst])
            edge_weights.append(weight)
        
        edge_index = torch.tensor(edge_index, dtype=torch.long).t().contiguous()
        edge_weights = torch.tensor(edge_weights, dtype=torch.float)
        
        # Create node features (simple one-hot or random)
        num_nodes = len(all_nodes)
        x = torch.randn(num_nodes, self.embedding_dim)
        
        return Data(x=x, edge_index=edge_index, edge_attr=edge_weights)
    
    def _build_nx_graph(self, edges_pdf: pd.DataFrame) -> nx.DiGraph:
        """Build NetworkX directed graph."""
        G = nx.DiGraph()
        
        for _, row in edges_pdf.iterrows():
            G.add_edge(row['prev'], row['curr'], weight=float(row['sum(n)']))
        
        return G
    
    def compute_embeddings_gnn(self, graph):
        """Compute embeddings using GraphSAGE."""
        import torch
        import torch.nn as nn
        from torch_geometric.nn import SAGEConv
        
        class GraphSAGE(nn.Module):
            def __init__(self, num_features, hidden_dim, num_layers=2):
                super().__init__()
                self.convs = nn.ModuleList()
                self.convs.append(SAGEConv(num_features, hidden_dim))
                for _ in range(num_layers - 1):
                    self.convs.append(SAGEConv(hidden_dim, hidden_dim))
            
            def forward(self, x, edge_index):
                for conv in self.convs:
                    x = conv(x, edge_index)
                    x = torch.relu(x)
                return x
        
        model = GraphSAGE(graph.x.size(1), self.embedding_dim)
        model.eval()
        
        with torch.no_grad():
            embeddings = model(graph.x, graph.edge_index)
        
        # Return as numpy array - would need proper node mapping for full implementation
        return embeddings.numpy()
    
    def compute_embeddings_node2vec(self, graph: nx.DiGraph) -> Dict[str, np.ndarray]:
        """Compute embeddings using node2vec."""
        node2vec = Node2Vec(graph, dimensions=self.embedding_dim, walk_length=30, num_walks=200)
        model = node2vec.fit(window=10, min_count=1)
        
        # Get embeddings for all nodes
        embeddings = {}
        for node in graph.nodes():
            embeddings[node] = model.wv[node]
        
        return embeddings
    
    def compute_embeddings_deepwalk(self, graph: nx.DiGraph) -> Dict[str, np.ndarray]:
        """Simple DeepWalk-style embedding using random walks."""
        # Simple implementation: use PageRank as a proxy for embeddings
        # In production, implement proper random walks
        pagerank = nx.pagerank(graph)
        
        # Create simple embeddings based on graph structure
        embeddings = {}
        for node in graph.nodes():
            # Use degree, pagerank, and neighbor features
            degree = graph.degree(node)
            pr = pagerank.get(node, 0.0)
            
            # Create embedding vector
            emb = np.zeros(self.embedding_dim)
            emb[0] = degree
            emb[1] = pr
            # Fill rest with random values based on node hash
            np.random.seed(hash(node) % 10000)
            emb[2:] = np.random.randn(self.embedding_dim - 2)
            
            embeddings[node] = emb
        
        return embeddings
    
    def compute_anomaly_scores(self, embeddings: Dict[str, np.ndarray], 
                              edges: pd.DataFrame) -> pd.DataFrame:
        """Compute anomaly scores based on embeddings."""
        scores = []
        
        for _, row in edges.iterrows():
            prev = row['prev']
            curr = row['curr']
            
            if prev in embeddings and curr in embeddings:
                prev_emb = embeddings[prev]
                curr_emb = embeddings[curr]
                
                # Compute distance/divergence
                distance = np.linalg.norm(prev_emb - curr_emb)
                
                # Normalize to [0, 1]
                # Use percentile-based normalization
                scores.append({
                    'prev': prev,
                    'curr': curr,
                    'gnn_score': float(distance)
                })
        
        scores_df = pd.DataFrame(scores)
        
        if len(scores_df) > 0:
            # Normalize scores to [0, 1]
            max_score = scores_df['gnn_score'].max()
            if max_score > 0:
                scores_df['gnn_score'] = scores_df['gnn_score'] / max_score
            
            # Flag anomalies based on percentile
            threshold = np.percentile(scores_df['gnn_score'], self.score_percentile)
            scores_df['gnn_flag'] = scores_df['gnn_score'] >= threshold
        else:
            scores_df['gnn_flag'] = False
        
        return scores_df
    
    def detect(self, df: DataFrame, months: List[str], target_month: str) -> DataFrame:
        """
        Detect anomalies using graph embeddings.
        
        Args:
            df: Clickstream DataFrame
            months: List of months
            target_month: Target month to analyze
            
        Returns:
            DataFrame with gnn_score and gnn_flag columns
        """
        if self.method == 'none':
            print("GNN detector disabled (no libraries available).")
            # Return empty DataFrame with correct schema
            return self.spark.createDataFrame([], schema="prev string, curr string, type string, month string, gnn_score double, gnn_flag boolean")
        
        print(f"Detecting anomalies using {self.method} method...")
        
        # Filter to target month
        month_data = df.filter(col("month") == target_month)
        
        # Build graph
        graph = self.build_graph(month_data)
        
        if graph is None:
            print("Warning: Could not build graph. Returning empty results.")
            return self.spark.createDataFrame([], schema="prev string, curr string, type string, month string, gnn_score double, gnn_flag boolean")
        
        # Compute embeddings
        if self.method == 'gnn' and PYG_AVAILABLE:
            embeddings_array = self.compute_embeddings_gnn(graph)
            # For GNN, we need to map back to edges
            # Simplified: use edge embeddings
            edges_pdf = month_data.select("prev", "curr", "type").distinct().toPandas()
            embeddings = {}  # Would need proper node mapping
        elif self.method in ['node2vec', 'deepwalk'] and nx is not None:
            embeddings = self.compute_embeddings_node2vec(graph) if self.method == 'node2vec' else self.compute_embeddings_deepwalk(graph)
            edges_pdf = month_data.select("prev", "curr", "type").distinct().toPandas()
        else:
            print("Warning: Graph method not available. Returning empty results.")
            return self.spark.createDataFrame([], schema="prev string, curr string, type string, month string, gnn_score double, gnn_flag boolean")
        
        # Compute anomaly scores
        scores_df = self.compute_anomaly_scores(embeddings, edges_pdf)
        
        # Add month and type columns
        scores_df['month'] = target_month
        scores_df['type'] = 'link'  # Default, would need to join from original data
        
        # Convert to Spark DataFrame
        result = self.spark.createDataFrame(scores_df)
        
        print(f"Computed GNN scores for {len(scores_df)} edges")
        
        return result

