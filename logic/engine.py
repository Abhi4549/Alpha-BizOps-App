# logic/engine.py

def create_tally_voucher_xml(voucher):
    """Voucher object ko Tally XML mein convert karna"""
    xml = f"""
    <VOUCHER VCHTYPE="{voucher.v_type}" ACTION="Create">
        <DATE>{voucher.date.replace('-', '')}</DATE>
        <PARTYLEDGERNAME>{voucher.party.name}</PARTYLEDGERNAME>
        <ALLLEDGERENTRIES.LIST>
            <LEDGERNAME>{voucher.party.name}</LEDGERNAME>
            <AMOUNT>{voucher.get_total()}</AMOUNT>
        </ALLLEDGERENTRIES.LIST>
        <NARRATION>{voucher.v_type} via Alpha Vyapar Pro</NARRATION>
    </VOUCHER>
    """
    return xml
