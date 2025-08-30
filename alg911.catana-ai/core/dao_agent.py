import json

class DAOAgent:
    def get_active_proposals(self):
        """
        Returns a list of active proposals from the DAO.
        """
        # Dummy data for now
        return [
            {"id": 1, "title": "Proposal to fund new research", "status": "active"},
            {"id": 2, "title": "Proposal to change governance structure", "status": "active"}
        ]

    def get_voting_power(self, user_id):
        """
        Returns the voting power of a given user.
        """
        # Dummy data for now
        return {"user_id": user_id, "voting_power": 100}

if __name__ == '__main__':
    agent = DAOAgent()
    print("Active Proposals:")
    print(json.dumps(agent.get_active_proposals(), indent=2))
    print("\nVoting Power for user 'test_user':")
    print(json.dumps(agent.get_voting_power('test_user'), indent=2))
