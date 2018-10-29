# Onering

Data representation and transformations are at the heart of everything we do and need.   The semantics of data (and their transformations and views) must be the same regardless of pesky barriers like frameworks, backends, languages, DSLs, libraries, data stores etc right?  

Unfortunately these pesky barriers are the reality and what cause the distortion in the model being represented in the most truthful way (which ever domain we pick - ER, OO, Documents etc).

So what we really need is a way to represent data in its truest form (again ER, OO, Documents etc) and then generate the real-world representation on the details that are in place (eg language, backends, data stores and their constraints etc).

Onering is a cross language, cross stack and portable polymorphic and strongly typed code generator for representing data in its truest form and *then* deriving the things necessary to work with real world barriers!

## Motivating Example

### Sample Application
Consider a system for managing musical albums, tracks, playlists, artists and users.   Some objects in this system are (without worrying about whether they are entities or relationships):

| Entities              	| Relationships/Collections     |
| :------------------- 	| :------------------- 		|
| Artist                 	| Album |
| Instrument                | Follows (following Artists or Venues to receive notification on changes) |
| Song                	 	| Event/Concert |
| Venue                 	| Playlist |
| User                 		| Track |
|                  		| Notification |
|                  		| Reactions (eg Shares/Comments/Likes) |

In a typical music player application we are interested in letting users uploading songs, tracks, albums (legally ofcourse) and organizing them into playlists and sharing them with other users.

### Data Models/Schemas

One "logical" representation without worrying about what our underlying systems give us would be:

```

// Some basic and native types in our system
native Any
native Byte
native Boolean
native Char
native Float
native Double
native Int
native Null
native Long
native String

# Native types do not have to be just basic ones like above.
# Reference types!
native Ref[T]
native Optional[T]
native Array[T]
native List[T]
native Map[K,V]
typeref DateTime = Long

union Json {
    listValue : List[Json]
    dictValue : Map[String, Json]
    stringValue : String
    longValue : Long
    doubleValue : Double
    booleanValue : Boolean
    nullValue : Null
}

record User {
    id : String
    name : String
    createdAt : DateTime
    updatedAt : DateTime
}

alias UserRef = Ref[User]

record Address {
    streetNumber : Int
    streetName : String
    city : String
    state : String
    country : String
    postcode : String?
}

record RecordBase {
    creator : UserRef
    createdAt : DateTime
    updatedAt : DateTime    
}

record Artist : RecordBase {
    id : String
    name : String
    address : Address?
    instruments : List[Ref[Instrument]]
    dateOfBirth : DateTime?
}

record Instrument : RecordBase {
    id : String
    name : String
    description : String
    url : URL
}

// A Song.  This is not the actual playable but only details
// about the original song as composed.
record Song : RecordBase {
    id : String
    title : String
    composer : String    // This should be typed but ok for now
    composedAt : DateTime
    lyricsUrl : URL?
}

record Venue : RecordBase {
    id : String
    name : String
    location : Address
    url : URL
}

record Event : RecordBase {
    name : String
    venue : Ref[Venue]
    date : DateTime
    artists : List[record ArtistRole {
         artist : Ref[Artist]
         role : String
    }]
}

record Track {
    song : Ref[Ref[Song]]
    streamingUrls : List[URL]
}

record Album : RecordBase {
    title : String
    event : Ref[Event]
    tracks : List[Track]
}

// A Playlist is a collection of entries - these could be albums or solo tracks
record Playlist : RecordBase {
	// Name of the playlist, eg "Kids Lullabies"
    name : String
    
    // Who this playlist belongs to
    owner : UserRef

    entries : List[Union {
    	album : Ref[Album]
        track : Ref[Track]
    }]
}

// We also have generic records!
record Follow[T] : RecordBase {
	follower : UserRef
    target : Ref[T]
    followedAt : DateTime
}

record Reaction[T] : RecordBase {
	// Who is posting a reaction?
    perfomer : UserRef
    
    // On what entity?
    source : Ref[T]
}

record Share[T] : Reaction[T] {
    title : String
    description : String
    previewImage : URL?
}

record Like[T] : Reaction[T] {
    likeCount : Int
}

record Comment[T] : Reaction[T] {
    text : String
    media : URL
}
```

### Schemas features

In the above notice we dont know what is an entity, or what is a relationship.  We are modelling in a way we (the modeller sees fit).   Coincidentally the above looks "like" an ER model.   


Some interesting things to point out above are:
* We describe our models with some basic constructs like records, unions, enums, primitive types.
* Primitive types (like String, Int etc) have no meaning.  Types are all pluggable.
* Complex types (records and unions) can inherit other records and inheritance is a matter of inclusion from a parent to a child type.
* Complex and Native types can be parametrized (fairly so in the inheritance chain).

Couple more of interesting choices:

* All entries are value types unless explicitly called out via the Ref wrapper type `Ref[T]` (or using `NativeTypes` (like List, String etc).
* Optionality is interesting since it only denotes the lack of a field value (whether it is a Reference or a Value).   Also Optionality **("?")** can be considered just shorthand for the type `Optional [T]`.
* Default values are not present above since the concept of a default is a serving or a storage artifact and even their semantic highly depandant on the systems that work with this data so they can be provided as annotations when required.

### Limitations

It is obvious that while the core data model for an application/system is easy to represent, its flow through the system is what is completely missing and where all the messiness creeps in.  How we model data ideally is almost always different from how other parts of the system see this (or some parts of this) data.   Some things that complicate matters are:

* What kind of serving framework are we using - restful?, rpc?
* What kind of transport mechanism?  xml/json/bson?  over Http?, websockets?, custom tcp?
* What storage and indexing platforms re we using and how does data get to those?   
* What transformations are required beyond the online world?
   * Ie for Kafka events,
   * Handling these nearline
   * In the offline world (no union support etc)

## Problem Statement


[This blog post](https://techcrunch.com/2018/10/28/the-tools-they-are-a-changing/) really summarizes the (amazing but paralyzing) world we live in.   There is a plenty of choice in the different parts of the stacks we use.   Though it would be ideal to come up with a data model first that highlights the features/relationships/constraints between the different parts and facets of data, modellers are forced to address limitations of systems first and then model data accordingly.   What if we could go the other way around?  Ie take the model of data as we see fit, and then plugin systems to process or wrap or work with the model?   After all data on its own is useless if it is not served/stored/transformed/processed.   

A typical application does not directly return/update the data model directly but does so parts of it.  For instance web clients have different view models from mobile (or "smaller") devices and the view models in turn may be composed of other view models or views.   Similarly when performing updates if the views/view models are used as a proxy for the update API, these would translate to real backend APIs responsible for certain parts of the data models.

Business logic (as validation and transformation) should kick in any time it is required (say in a responsive SPA or in an API backend or even in offline analysis).   Currently this requires replication that is very specific to the tier it is hosted in and intents cannot easily be shared.   

And to make this all murkier, People’s choice of languages and frameworks and tooling are arbitrary and is (and fairly so) a matter of personal taste.  What is required is a system that allows a design of a system that starts with the modelling of the data followed by the derivation of data into different systems along with the transformation that makes this derivation possible.  Finally we want these transformations to be composable, reusable and plugable so the boilerplate of dealing with language/framework/platform specific details do not leak into the actual work designers would be interested in doing.

## Onering

Onering is *not* a language.   It is instead a DSL for declaring data models, schemas, derivations (between platforms) and transformations between derivations so that platform specific processors can generate the artifacts they need to hook a new platform (language and/or framework) to work with and add value to the data model.

Diving right back into the motivating example.   We had earlir described the model of our data in the application's universe.   Without it being stored it is useless.  Where do we store it?  There are plenty of choices, Relational, Document, No-SQl, Graph and so on.   So many choices!   Let us pick one and dive right in.  Let us store our model into a relational DB.   A relational store cannot store our data as is.  It requires some transformation.   But before we describe a transformation we want to specify some derivations that will help us hint data transformations so that any system.  An example will make it clear.

Consider the User model in our logical world (above).   As a table in a relational DB we expect it to be something like:

```
table User
```

This is what onering is for.  A resource/entity is described ones along with the validators and transformers that it needs.  However these transformers and validators are not implemented in onering (Onering is *not* a language).   These transformers and validators are described via strongly typed (even polymorphic) function signature that can be “injected” when a new language is used.

Examples:

* Rest API  ->  Django ORM
* Rest API  ->  Appengine backend
* Rest API (Restli) -> Flask -> App Engine

What do we want onering to do here?

There are two scenarios.   

1. Web app frameworks that take a HttpRequest -> ResourceHandler
2. Restful frameworks that auto convert a HttpRequest -> Typed Resource (applying some validations) -> ResourceHandler

In both cases, ResourceHandler needs to convert to a storage object and save.  This means we either need to convert a way to convert a typed Restful resource into a storage resource with transforms included.   This is the same way a HttpRequest can be transformed to a RestResource.

### Basic Resource Schemas

So Onering has a model DSL.  As a model DSL, we expect basic things:

NativeTypes	-	Basic opaque types to be “provided” by environment - eg Int, FILE, Array, Map, etc
TypeVar	-	Type variables that are used to bind a type to somewhere in a context.
FunctionType	-	To declare and specify function signatures.
RecordType	-	For named product types
TupleType	-	For unnamed tuple types
UnionType	-	Named sum types

Given this we can define records as so:

```
# Some basics:

record Person {
   id : String
   name : String
   dateOfBirth : Optional[DateTime]
   address : union AddressInfo {
        homeAddress : Address
        companyAddress : Address
   }
}

record Address {
    streetNumber : Int
    streetName : String
    city : String
    state : String
    country : String
    postcode : Optional[String]
}
```

Correspondingly our restful api for a person could be a typical CRUD api whose resource handlers could correspond to:

```
def createPerson(person : Person) -> Person:
    …

def getPerson(id : String) -> Person:
    …

def deletePerson(id : String) -> Boolean:
    …

def updatePerson(patch : List[PatchOp[Person]]) -> Boolean:
    … 
# Where Patch is:
typedef PatchApplyFunc[R] :: R -> R
typeclass PatchOp[R]:
    apply :: PatchApplyFunc
```


Now looking at the above we know exactly what the “rest” API would look like.  One of the many things we dont yet know is when the resource handler is invoked how are the parameters extracted from the request object, eg HttpRequest.

Let us define a HttpRequest type for it:

```
    record File {
        /**
         * Path of the file used as attachments.
         */
        path : String

        /**
         * Content type of the file.
         */
        contentType : String
    }

    /**
     * Payload can either be raw data or a dictionary of key/value pairs
     */
    union Payload {
        rawData : Stream[Byte]
        fileData : File
        kvPairs : Map[String, Payload]
    }

    /**
     * Defines a generic http request that is sent to any API
     * server that is based on http.
     */
    record HttpRequest {
        method : String
        path : String
        contentType : String
        args : Map[string, string]

        /**
         * headers of the form part.
         */
        headers : Map[String, List[String]]

        /**
         * Content of the request otherwise.
         */
        body : Payload
    }
```

A lot is going on here.  Here we just defined a HttpRequest but no way to actually convert this into a People resource.
