from algopy import ARC4Contract, Global, UInt64, arc4, Txn, BoxMap, Account

# Updated HandshakeRecord struct with notes
class HandshakeRecord(arc4.Struct):
    handshake_id: arc4.UInt64
    initiator: arc4.Address
    receiver: arc4.Address
    timestamp: arc4.UInt64
    note: arc4.String  # NEW: Add note field

class HandshakeContract(ARC4Contract):
    def __init__(self) -> None:
        self.counter = UInt64(0)
        self.handshakes = BoxMap(UInt64, HandshakeRecord)
        self.user_handshakes = BoxMap(Account, arc4.DynamicArray[arc4.UInt64])
   
    @arc4.abimethod
    def create_handshake(self, other_user: arc4.Address, note: arc4.String) -> arc4.UInt64:
        # Get the caller
        sender = Txn.sender
       
        # Convert other_user to native for comparison
        other_user_native = other_user.native
       
        # Validation: Can't handshake yourself
        assert sender != other_user_native
       
        # Get current timestamp
        current_time = Global.latest_timestamp
       
        # Generate unique handshake ID
        handshake_id = self.counter
        self.counter += UInt64(1)
       
        # Create and store handshake record WITH NOTE
        handshake_record = HandshakeRecord(
            handshake_id=arc4.UInt64(handshake_id),
            initiator=arc4.Address(sender),
            receiver=other_user,
            timestamp=arc4.UInt64(current_time),
            note=note  # NEW: Store the note
        )
       
        # Store the handshake record
        self.handshakes[handshake_id] = handshake_record.copy()
       
        # Add to initiator's handshake list
        if sender in self.user_handshakes:
            initiator_list = self.user_handshakes[sender].copy()
            initiator_list.append(arc4.UInt64(handshake_id))
            self.user_handshakes[sender] = initiator_list.copy()
        else:
            new_list = arc4.DynamicArray(arc4.UInt64(handshake_id))
            self.user_handshakes[sender] = new_list.copy()
       
        # Add to receiver's handshake list
        if other_user_native in self.user_handshakes:
            receiver_list = self.user_handshakes[other_user_native].copy()
            receiver_list.append(arc4.UInt64(handshake_id))
            self.user_handshakes[other_user_native] = receiver_list.copy()
        else:
            new_list = arc4.DynamicArray(arc4.UInt64(handshake_id))
            self.user_handshakes[other_user_native] = new_list.copy()
       
        return arc4.UInt64(handshake_id)

    @arc4.abimethod
    def update_handshake_note(self, handshake_id: arc4.UInt64, new_note: arc4.String) -> None:
        """Update the note of an existing handshake (only by participants)"""
        sender = Txn.sender
        
        # Get existing handshake with .copy()
        handshake = self.handshakes[handshake_id.native].copy()
        
        # Only initiator or receiver can update note
        assert sender == handshake.initiator.native or sender == handshake.receiver.native
        
        # Update the note
        updated_handshake = HandshakeRecord(
            handshake_id=handshake.handshake_id,
            initiator=handshake.initiator,
            receiver=handshake.receiver,
            timestamp=handshake.timestamp,
            note=new_note  # Update with new note
        )
        
        # Store updated record
        self.handshakes[handshake_id.native] = updated_handshake.copy()
   
    @arc4.abimethod
    def get_counter(self) -> arc4.UInt64:
        return arc4.UInt64(self.counter)
   
    @arc4.abimethod
    def get_handshake(self, handshake_id: arc4.UInt64) -> HandshakeRecord:
        return self.handshakes[handshake_id.native]

    @arc4.abimethod
    def get_user_handshakes(self, user: arc4.Address) -> arc4.DynamicArray[arc4.UInt64]:
        """NEW: Get all handshake IDs for a specific user"""
        if user.native in self.user_handshakes:
            return self.user_handshakes[user.native]
        else:
            # Return empty array if user has no handshakes
            return arc4.DynamicArray[arc4.UInt64]()