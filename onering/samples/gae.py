
/**
 * This file declares some of the built-in types and records in google appengine data store.  
 * Note that the interesting bits are the atom that are predefined but all record types can 
 * be declared in terms of these atoms.
 */
namespace onering.gae.types {
    atomic Byte
    atomic Integer
    atomic Long
    atomic Float
    atomic String
    atomic Text
    atomic Date
    atomic Array<T>
    atomic List<T> 
    atomic Map<K,V> 

    record GeoPt {
        latitude : Float
        longitude : Float
    }

    record ShortBlob {
        bytes : Array<Byte>
    }

    record Blob {
        bytes : Array<Byte>
    }

    record PostalAddress {
        address : String
    }

    record PhoneNumber {
        number : String
    }

    record Email {
        email : String
    }

    record User {
        authDomain : String
        userId : String
        federatedIdentity : String
        email : String
        nickname : String
    }

    record IMHandle {
        address : String
        protocol : String
    }

    record Link {
        value : String
    }

    record Category {
        category : String
    }

    record Rating {
        rating : String
    }

    record Key {
        appId : String
        id : Long
    }
}
