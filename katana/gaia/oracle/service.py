from katana.gaia.oracle.models import SpecialistProfile

class OracleService:
    async def build_profile(self, username: str) -> SpecialistProfile:
        ...
