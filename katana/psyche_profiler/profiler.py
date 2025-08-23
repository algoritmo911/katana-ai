import logging
from typing import Optional, List, Dict, Any
from supabase import Client

# Initialize logger
logger = logging.getLogger(__name__)

class PsycheProfiler:
    """
    The Psyche Profiler daemon. It analyzes user interactions to derive ethical
    archetypes and stores them in the Archetype Library.
    """
    def __init__(self, supabase_client: Optional[Client]):
        """
        Initializes the PsycheProfiler.

        Args:
            supabase_client: An initialized Supabase client.
        """
        self.client = supabase_client
        if self.client:
            logger.info("PsycheProfiler initialized with Supabase client.")
        else:
            logger.warning("PsycheProfiler initialized without a Supabase client. It will not be functional.")

    def _fetch_interaction_data(self) -> List[Dict[str, Any]]:
        """
        Fetches unprocessed interaction data from the oracle_interactions table.
        """
        if not self.client:
            logger.warning("No client available. Cannot fetch interaction data.")
            return []

        logger.info("Fetching data from oracle_interactions table...")
        try:
            # In a real implementation, we would filter for unprocessed records, e.g., .eq("processed", False)
            response = self.client.table("oracle_interactions").select("*").execute()
            if response.error:
                logger.error(f"Error fetching interaction data: {response.error}")
                return []
            logger.info(f"Fetched {len(response.data)} interaction records.")
            return response.data
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching data: {e}", exc_info=True)
            return []

    def _cluster_decisions(self, interactions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Clusters user decisions based on their implicit ethical preferences.
        (Placeholder)
        """
        logger.info("Clustering decisions into ethical schools...")
        # This is where a real ML clustering model would run.
        # For now, we'll hardcode two clusters if data is available.
        if not interactions:
            return {}

        mock_clusters = {
            "Utilitarian": [interactions[0]],
            "Deontological": interactions[1:]
        }
        logger.info(f"Successfully clustered interactions into {len(mock_clusters)} schools (mocked).")
        return mock_clusters

    def _create_archetypes(self, clusters: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Creates structured AI archetype profiles from clustered data.
        (Placeholder)
        """
        logger.info("Creating AI archetype profiles from clusters...")
        archetypes = []
        for school, members in clusters.items():
            if not members:
                continue
            archetype = {
                "name": f"Archetype-{school}-{len(members)}",
                "description": f"An archetype representing the {school} school of thought.",
                "ethical_school": school,
                "reward_function": {"goal": f"maximize_{school.lower()}_outcome", "parameters": {"sample_size": len(members)}}
            }
            archetypes.append(archetype)
        logger.info(f"Created {len(archetypes)} new archetype profiles (mocked).")
        return archetypes

    def _save_archetypes(self, archetypes: List[Dict[str, Any]]):
        """
        Saves the newly generated archetypes to the archetype_library table.
        """
        if not self.client:
            logger.warning("No client available. Cannot save archetypes.")
            return

        if not archetypes:
            logger.info("No new archetypes to save.")
            return

        logger.info(f"Saving {len(archetypes)} archetypes to the archetype_library...")
        try:
            response = self.client.table("archetype_library").insert(archetypes).execute()
            if response.error:
                logger.error(f"Failed to save archetypes: {response.error}")
            else:
                logger.info("Successfully saved archetypes.")
        except Exception as e:
            logger.error(f"An unexpected error occurred while saving archetypes: {e}", exc_info=True)

    def run_profiling(self):
        """
        Executes the full profiling pipeline.
        """
        logger.info("Starting Psyche Profiler run...")
        if not self.client:
            logger.error("PsycheProfiler cannot run without a database client.")
            return

        # 1. Fetch data
        interactions = self._fetch_interaction_data()
        if not interactions:
            logger.info("No new interactions to process. Ending run.")
            return

        # 2. Cluster decisions
        clusters = self._cluster_decisions(interactions)

        # 3. Create archetypes
        archetypes = self._create_archetypes(clusters)

        # 4. Save archetypes to the library
        self._save_archetypes(archetypes)

        logger.info("Psyche Profiler run finished successfully.")
