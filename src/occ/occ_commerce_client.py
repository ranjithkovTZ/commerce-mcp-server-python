from __future__ import annotations

from destination_details import DestinationDetails
from occ.occ_commerce_auth import OccCommerceTokenProvider, load_occ_commerce_credentials


class OccCommerceClient:
    """Produces DestinationDetails by talking directly to SAP Commerce Cloud's
    OCC API, no BTP Destination service involved."""

    def __init__(self):
        self._creds = load_occ_commerce_credentials()
        self._token_provider = OccCommerceTokenProvider(self._creds)

    def get_destination(self, destination_name: str | None = None) -> DestinationDetails:
        """Get the destination details for the OCC backend.

        Args:
            destination_name (str | None): Optional name to label the destination.

        Returns:
            DestinationDetails: The details of the destination.
        """
        token = self._token_provider.get_access_token()
        return DestinationDetails(
            name=destination_name or "occ",
            url=self._creds.base_url,
            authentication="OAuth2ClientCredentials",
            auth_header=f"Bearer {token}",
            username=self._creds.client_id,
            password=None,
            base_site_id=self._creds.base_site_id,
        )
