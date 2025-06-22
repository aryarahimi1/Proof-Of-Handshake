import streamlit as st
import algokit_utils
from algosdk.v2client import algod
from algosdk.kmd import KMDClient
from algosdk.atomic_transaction_composer import AccountTransactionSigner
from smart_contracts.artifacts.handshake.handshake_contract_client import HandshakeContractClient

# ─── CLIENT SETUP ──────────────────────────────────────────────────────────────
ALGOD_TOKEN = ""
ALGOD_ADDRESS = "http://localhost:4001"
KMD_TOKEN = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
KMD_ADDRESS = "http://localhost:4002"
HEADERS = {"User-Agent": "algosdk"}

algod_client = algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS, HEADERS)
kmd = KMDClient(KMD_TOKEN, KMD_ADDRESS)
wallets = kmd.list_wallets()
default_wallet = next((w for w in wallets if w.get("name") == "unencrypted-default-wallet"), wallets[0])
handle = kmd.init_wallet_handle(default_wallet["id"], "")
accounts = kmd.list_keys(handle)

# Create AlgorandClient for the contract client
try:
    algorand = algokit_utils.AlgorandClient(algod_client=algod_client)
except:
    try:
        algorand = algokit_utils.AlgorandClient(algod=algod_client)
    except:
        algorand = algokit_utils.AlgorandClient.default_localnet()

st.sidebar.header("Account Selection")

# Let user pick an account
selected_address = st.sidebar.selectbox("Choose Account:", accounts)

if selected_address:
    # Get private key for signing
    private_key = kmd.export_key(handle, "", selected_address)
    signer = AccountTransactionSigner(private_key)
    
    # Check account balance using the working algorand client
    try:
        account_info = algorand.account.get_information(selected_address)
        balance_algos = account_info.amount / 1_000_000
        min_balance_algos = account_info.min_balance / 1_000_000
        
        st.sidebar.success(f"Connected: {selected_address[:8]}...")
        st.sidebar.write(f"Balance: {balance_algos:.6f} ALGO")
        st.sidebar.write(f"Min Balance: {min_balance_algos:.6f} ALGO")
    except Exception as e:
        st.sidebar.warning(f"Could not get balance: {e}")
        st.sidebar.success(f"Connected: {selected_address[:8]}...")
    
    # Your deployed contract App ID (replace with your actual App ID)
    APP_ID = st.sidebar.number_input("Enter your Contract App ID:", min_value=1, value=1)  # Try App ID 1 first!
    
    # Connect to your contract with selected account
    client = HandshakeContractClient(
        algorand=algorand, 
        app_id=APP_ID,
        default_sender=selected_address,
        default_signer=signer
    )

st.title("🤝 Handshake Contract")

# Only show main interface if account is connected
if 'client' in locals():
    st.write(f"**Connected Account:** {selected_address}")
    st.write(f"**Contract App ID:** {APP_ID}")
    
    # Try to get counter to verify contract exists
    try:
        counter = client.send.get_counter().abi_return
        st.metric("Total Handshakes", counter)
        
        # Create tabs for different features
        tab1, tab2, tab3 = st.tabs(["Create Handshake", "My Handshakes", "View Handshake"])
        
        with tab1:
            st.subheader("🤝 Create New Handshake")
            
            # Wallet name storage (local for now)
            if 'wallet_names' not in st.session_state:
                st.session_state.wallet_names = {}
            
            other_address = st.text_input("Enter wallet address:", key="new_handshake")
            
            wallet_name = st.text_input("Give this wallet a name (optional):", key="wallet_name")
            if wallet_name and other_address:
                st.session_state.wallet_names[other_address] = wallet_name
            
            # Display stored name if exists
            if other_address and other_address in st.session_state.wallet_names:
                st.write(f"💫 **Known as:** {st.session_state.wallet_names[other_address]}")
            
            # FORCE SHOW NOTE INPUT - Make it very visible
            st.markdown("---")  # Add separator
            st.markdown("### 📝 **Add a note about this handshake:**")
            st.write("*Where did you meet? What was the context?*")
            
            note = st.text_area(
                "Write your note here:", 
                placeholder="e.g., 'Met at Consensus 2025 during the AlgoPy workshop'\n'Coffee meeting at Starbucks downtown'\n'Networking event at ETH Denver'",
                height=120,
                key="handshake_note",
                help="This note will be stored on the blockchain with your handshake"
            )
            
            # Show what will be saved
            if note:
                st.success(f"📝 Note to save: '{note}'")
            else:
                st.warning("⚠️ No note entered - will save as 'No note added'")
            
            st.markdown("---")  # Add separator
            
            if st.button("🤝 Create Handshake", key="create_btn") and other_address:
                try:
                    if len(other_address) != 58:
                        st.error("Invalid address length. Should be 58 characters.")
                    else:
                        # Make sure we have a note, even if empty
                        final_note = note.strip() if note else "No note added"
                        st.info(f"Creating handshake with note: '{final_note}'")
                        
                        # Try the new method signature first, fall back to old
                        try:
                            # NEW contract with notes
                            result = client.send.create_handshake((other_address, final_note))
                            st.success(f"✅ Handshake created! ID: {result.abi_return}")
                            st.success(f"📝 Note saved: '{final_note}'")
                        except Exception as note_error:
                            if "note" in str(note_error).lower():
                                # OLD contract without notes
                                result = client.send.create_handshake((other_address,))
                                st.success(f"✅ Handshake created! ID: {result.abi_return}")
                                st.warning(f"⚠️ Note '{final_note}' not saved - using old contract")
                            else:
                                raise note_error
                        st.balloons()
                except Exception as e:
                    st.error(f"Error creating handshake: {e}")
                    # Show if it's a contract method issue
                    if "no attribute" in str(e):
                        st.error("⚠️ Your contract needs to be updated to support notes!")
        
        with tab2:
            st.subheader("📋 My Handshakes")
            
            # For now, we'll need to check each handshake ID manually
            # since your contract doesn't have a "get_user_handshakes" method yet
            st.info("Searching through all handshakes to find yours...")
            
            my_handshakes = []
            for handshake_id in range(counter):
                try:
                    handshake = client.send.get_handshake((handshake_id,)).abi_return
                    if handshake.initiator == selected_address or handshake.receiver == selected_address:
                        my_handshakes.append((handshake_id, handshake))
                except:
                    continue
            
            if my_handshakes:
                for handshake_id, handshake in my_handshakes:
                    with st.expander(f"Handshake #{handshake_id}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Initiator:**")
                            initiator_name = st.session_state.wallet_names.get(handshake.initiator, "Unknown")
                            st.write(f"{initiator_name}")
                            st.code(handshake.initiator, language=None)
                            
                        with col2:
                            st.write("**Receiver:**")
                            receiver_name = st.session_state.wallet_names.get(handshake.receiver, "Unknown")
                            st.write(f"{receiver_name}")
                            st.code(handshake.receiver, language=None)
                        
                        import datetime
                        timestamp = datetime.datetime.fromtimestamp(handshake.timestamp)
                        st.write(f"**When:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        # NEW: Display note prominently
                        st.write("**📝 Note:**")
                        if hasattr(handshake, 'note') and handshake.note and handshake.note != "No note added":
                            st.info(f"💬 {handshake.note}")
                        else:
                            st.warning("_No note added_")
                        
                        # Role indicator
                        role = "Initiator" if handshake.initiator == selected_address else "Receiver"
                        if role == "Initiator":
                            st.success(f"👤 {role}")
                        else:
                            st.info(f"🤝 {role}")
                        
                        # NEW: Edit note functionality (now that contract supports it)
                        edit_key = f"editing_{handshake_id}"
                        if edit_key not in st.session_state:
                            st.session_state[edit_key] = False
                            
                        if not st.session_state[edit_key]:
                            if st.button(f"✏️ Edit Note", key=f"edit_btn_{handshake_id}"):
                                st.session_state[edit_key] = True
                                st.rerun()
                        else:
                            st.write("**Update Note:**")
                            current_note = handshake.note if hasattr(handshake, 'note') else ""
                            new_note = st.text_area(
                                "New note:", 
                                value=current_note, 
                                key=f"note_edit_{handshake_id}",
                                height=100
                            )
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button(f"💾 Save", key=f"save_{handshake_id}"):
                                    try:
                                        client.send.update_handshake_note((handshake_id, new_note))
                                        st.success("Note updated!")
                                        st.session_state[edit_key] = False
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error updating note: {e}")
                                        if "no attribute" in str(e):
                                            st.error("⚠️ Your contract doesn't have update_handshake_note method yet!")
                            
                            with col2:
                                if st.button(f"❌ Cancel", key=f"cancel_{handshake_id}"):
                                    st.session_state[edit_key] = False
                                    st.rerun()
            else:
                st.info("No handshakes found for your account.")
        
        with tab3:
            st.subheader("🔍 View Specific Handshake")
            
            if counter > 0:
                handshake_id = st.number_input("Enter Handshake ID:", min_value=0, max_value=max(0, counter-1), value=0)
                
                if st.button("Get Handshake Details"):
                    try:
                        handshake = client.send.get_handshake((handshake_id,)).abi_return
                        
                        st.success(f"Handshake #{handshake_id} Details:")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**Initiator:**")
                            initiator_name = st.session_state.wallet_names.get(handshake.initiator, "Unknown")
                            st.write(f"{initiator_name}")
                            st.code(handshake.initiator, language=None)
                            
                        with col2:
                            st.write("**Receiver:**")
                            receiver_name = st.session_state.wallet_names.get(handshake.receiver, "Unknown")
                            st.write(f"{receiver_name}")
                            st.code(handshake.receiver, language=None)
                        
                        import datetime
                        timestamp = datetime.datetime.fromtimestamp(handshake.timestamp)
                        st.write(f"**Timestamp:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        # NEW: Display note prominently
                        st.write("**📝 Note:**")
                        if hasattr(handshake, 'note') and handshake.note and handshake.note != "No note added":
                            st.info(f"💬 {handshake.note}")
                        else:
                            st.warning("_No note added_")
                        
                    except Exception as e:
                        st.error(f"Error getting handshake: {e}")
            else:
                st.info("No handshakes created yet. Create your first handshake in the 'Create Handshake' tab!")
                
    except Exception as e:
        st.error(f"Error connecting to contract: {e}")
        st.info("Check if:")
        st.write("1. App ID is correct")
        st.write("2. Contract is deployed on LocalNet") 
        st.write("3. Contract address has enough balance for box storage")
        
else:
    st.info("Please select an account from the sidebar to continue.")