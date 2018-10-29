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

### Base schemas

Diving right back into the motivating example.   We had earlir described the model of our data in the application's universe.   Without it being stored it is useless.  Where do we store it?  There are plenty of choices, Relational, Document, No-SQl, Graph and so on.   So many choices!   Let us pick one and dive right in.  Let us store our model into a relational DB.   A relational store cannot store our data as is.  It requires some transformation.   But before we describe a transformation we want to specify some derivations that will help us hint data transformations so that any system.  An example will make it clear.

We want our logical data model above to map something similar to what is below for kosher consumption by a relation DB.

First starting with the User record and its equivalent:

```
@sql.table(name = "users")
record User {
	@sql.primarykey
    id : String
    
    @sql.constraint(blank = False, null = False)
    name : String
    
    @sql.default(auto_now = True)
    createdAt : DateTime
    
    @sql.default(auto_now = True)
    updatedAt : DateTime
}
```

Nothing magical above.  Tables can be records with annotation without loss of generality.   A record can be marked as a persistable entry with the `@sql.table` annotation above.   This way the ORM toolchain gets hints as to the the name of the table in which this data will be read from/written to.

Not all records need a table annotation:

```
record Address {
    streetNumber : Int
    streetName : String
    city : String
    state : String
    country : String
    postcode : String?
}
```

The Address cannot be persisted and has to be used in a flattened way.

Now let us introduce some constraints onto the fields.  Again nothing fancy.  Annotations help indicate to the toolchain that is consuming this (SQL/ORM) as to what validation to put in place and when.

```
@sql.table(name = "instruments")
record Instrument : RecordBase {
	@sql.primarykey
    id : String
    
    @sql.constraints(null = False, blank = False)
    name : String
    
    @sql.max_length(512)
    description : String
    
    @sql.null(True)
    url : URL
}
```

Just declaring bits of base tables is no fun.  We ultimately do want relations between tables.  The Artist is perfect:

```
record Artist : RecordBase {
	@sql.primarykey
    id : String
    
    @sql.constraints(null = False, blank = False)
    name : String
    
    // how do we use the address
    @sql.flatten(prefix = "address_")
    address : Address
    
    @sql.constraints(null = True)
    dateOfBirth : DateTime
    
    // instruments : List[Ref[Instrument]]
}
```

First thing to note is the "flatten" annotation that takes a complex type and flattens it into multiple fields with a given prefix.  This would result in an error if a flattened field already exists.

Secondly and more interestingly is how can we model instruments?  We know instruments are a many-to-many relation between an Artist and the Instruments she plays.   An easy way is to simply create a new ArtistInstrument record as something like:

```
@sql.table(name = "artist_instruments")
@sql.constraint(unique_together = ["artist", "instrument"])
record ArtistInstrument {
    @sql.ForeignKey(Artist)
    artist : Ref[Artist]
    
    @sql.ForeignKey(Instrument)
    instrument : Ref[Instrument]
    
    // When the artist declared his love/proficiency for this instrument?
    registeredAt : DateTime
}
```

### Derivations

The above helps us model "target" schemas easily and until now nothing new or major has been demonstrated beyond a new schema DSL.   In fact the above strategy has the disadvantage that even though we can define annotations and let the tool use them, the linkage between a vanilla Artist and the SQL Artist are not obvious.  A backend that converts an Artist retrieved from a SQL backend and converting it to an Artist in the ViewModel would have no idea that the name fields are the same (let alone when there may be a renaming).

In order to do this, we need derivations that can generate target schemas while maintaining these logical linkages.

What is required is something along the lines of:

Starting with the easier User record - let us put it in a different namespace to differentiate from the original data model:

```
namespace org.onering.samples.sql {
    @sql.table(name = "users")
    record User derives org.onering.samples.vanilla.User {
        @sql.primarykey
        id

        @sql.constraint(blank = False, null = False)
        name

        @sql.default(auto_now = True)
        createdAt : Long

		// Let Onering find a DataTime to Long transformer
        @sql.default(auto_now = True)
        updatedAt as updatedOn : Long
        
        // or specify a custom transformer - note DateTime2Long tells
        // us what the target type will be!
        @sql.default(auto_now = True)
        updatedAt as updatedOn using DateTime2Long
    }
}
```

A few interesting things above:
1. A derived record simply "derives" a source record.  This by default gives it all the fields in the source record.
2. From this point on derived fields can just be specified without their type.  This indicates that in the new record it has the same type as in the source record.
3. The `createdAt` and `updatedOn` fields are interesting.  They indicate a change in type.   The conversion between a DateTime (whatever that is) to a Long is Onering's job!!  
4. `updatedOn` is a field renaming and is semantically linked to the `updatedAt` field in the source record.
5. Annotations still dont mean anything they are just passed onto the processors.

Before proceeding further, this has enough information to give us a target User record that is equivalent to the below record without actually typing it up but also maintaining linkages across fields:

```
namespace org.onering.samples.sql {
    @sql.table(name = "users")
    record User {
        @sql.primarykey
        id : String

        @sql.constraint(blank = False, null = False)
        name : String

        @sql.default(auto_now = True)
        createdAt : Long

        @sql.default(auto_now = True)
        updatedOn : Long
    }
}
```

### Projections
