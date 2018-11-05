# Onering


## Background

We live in an [amazing (but paralyzing)](https://techcrunch.com/2018/10/28/the-tools-they-are-a-changing/) world full of choices in tools and tech stacks.  It used to be that data models were a definitive guide to a modeller's intent highlighting the features/relationships/constraints between the different parts and facets of data.  However due to the plethora of choices in technologies (and their constraints) addressing limitations of systems takes precedence over sound data modelling.   How can we go back to the other way around?  Ie take the model of data as we see fit, and then plugin systems to process or wrap or work with the model?   After all data on its own is useless if it is not served/stored/transformed/processed.     

The semantics of data (and their transformations and views) must be the same regardless of barriers like frameworks, backends, languages, DSLs, libraries, data stores etc?  Unfortunately these barriers are the reality and what cause the distortion in the model being represented in the most truthful way (which ever domain we pick - ER, OO, Documents etc).

A typical application does not directly return/update the data model directly but does so to parts of it in different phases.  For instance web clients have different view models from mobile (or "smaller") devices and the view models in turn may be composed of other view models or views.   Similarly when performing updates if the views/view models are used as a proxy for the update API, these would translate to real backend APIs responsible for certain parts of the data models.

Business logic (as validation and filtering) should kick in any time it is required (say in a responsive SPA or in an API backend or even in offline analysis).   Currently this requires replication that is very specific to the tier it is hosted in and intents cannot easily be shared.   

We propose **Onering**.   Onering is a cross language, cross stack and portable polymorphic and strongly typed code generator for representing data in its truest form and *then* enabling pluggable derivations necessary to work in the real world!


## Motivating Example

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

## Onering Basics

### Native Types

To represent our models we will need some basic types.  There are no built in types in Onering.  These can just be declared as a native type:

```
// Some basic and native types in our system
native Any
native Byte
native Boolean
native Char
native Float
native Double
native Int
native Long
native String

// Native types do not have to be just basic ones like above.  
// They can also be parametrized (more on parametrized types later).
native Optional[T]
native Array[T]
native List[T]
native Map[K,V]
native Ref[T]	// References are native types too
```

Native types have no meaning and are completely pluggable by the modeller.

### Composite Types

We can represent the logical view of this data in a simple way.  This would include both the structure as well as the constraints and validations we expect on the data.  Note that validation being here makes sense since this is a way to ensure that bad/invalid data does not stay at the logical level.   

One "logical" representation without worrying about what our underlying systems give us (but with validation rules) would be:

A user record can be defined as:

```
record User {
	@unique
    id : String
    
    @EnsureNonEmpty()
    name : String

	createdAt : DateTime

	updatedAt : DateTime
}
```

The above User record has a few fields and importantly a few annotations on a few of the fields.  

### Aliases

The User is integral to several parts of the system so we can expect to see it referenced in several other types.  The `creator` field below is an example of this:

```
alias DateTime = Long

record EntityBase {
    @unique
    id : String
    creator : Ref[User]
    createdAt : DateTime
    updatedAt : DateTime    
}
```

We can simplify this by creating aliases:

```
alias UserRef = Ref[User]
```

thus turning the `EntityBase` into:

```
record EntityBase {
    @unique
    id : String
    
    creator : UserRef
    
    createdAt : DateTime
    updatedAt : DateTime    
}
```

### RefinedTypes

We also expect annotations to be used commonly.  For instance the `@unique` attribute on the `id` field in the `EntityBase`.  We can shortcut this with `RefinedType` (TODO: Can this actually just be done with an alias too if aliases themselves do not need any annotations?):

```
@unique
refined UniqueId = String

@EnsurePositive
refined PositiveInt = Int

@EnsureNonEmpty
refined NonEmptyString = String

```

... further simplifying `EntityBase` into:

```
record EntityBase {
    id : UniqueId
    
    creator : UserRef
    
    createdAt : DateTime
    updatedAt : DateTime    
}
```

Multiple annotations (with arguments) can also be applied on RefinedTypes:

```
@EnsureNonEmpty
@EnsureEvenLength
@MaxLength(32)
refined EvenLengthString = String
```

**TODO**: Define the signature of an annotation on a refined type (to include error handling).

### Includes

Often models need to reuse common parts.  For example in our model all persistable fields need `id`, `creator`, and created/deleted timestamps.  This is captured in the `EntityBase` record which can be included with:

```
record Venue {
    #include EntityBase
    
    name : NonEmptyString
    
    location : Address
    
    url : URL
}


record Address {
    streetNumber : PositiveInt
    
    streetName : NonEmptyString
    
    city : NonEmptyString

	state : NonEmptyString
    
    @EnsureValidCountryCode
    country : String
    
    postcode : String?
}
```


### Parametrized Types

Sometimes we need polymorphic behavior over the types and type parametrization can help with structuring common fields regardless of types:

Consider user actions on entities 
```
record Follow[T] {
    #include EntityBase
    
	follower : UserRef
    
    target : Ref[T]
    
    followedAt : DateTime
}

record Reaction[T] {
    #include EntityBase
    
	// Who is posting a reaction?
    actor : UserRef
    
    // On what entity?
    source : Ref[T]
}

record Share[T] {
	#include Reaction[T]
    
    title : String
    
    description : String
    
    previewImage : URL?
}

record Like[T] {
	#include Reaction[T]
    
    likeCount : Int
    
    likeType : enum LikeType {
        LIKE,
        ANGRY,
        HATE,
        WOW,
        CONFUSED,
        SAD
    }
}

record Comment[T] {
	#include Reaction[T]
    
    text : String
    
    media : URL
}
```

### Data model
We can go on to describe the rest of the data model:

```
record Artist {
	#include EntityBase
    
    name : NonEmptyString

	address : Address?
    
    instruments : List[Ref[Instrument]]
    
    dateOfBirth : DateTime?
}

record Instrument {
	#include EntityBase
    
    name : NonEmptyString    
    description : String
    url : URL
}

// A Song.  This is not the actual playable but only details
// about the original song as composed.
record Song {
	#include EntityBase
    
    title : NonEmptyString
    
    composer : NonEmptyString    // This should be typed but ok for now
    
    composedAt : DateTime
    
    lyricsUrl : URL?
}

record Event {
	#include EntityBase
    
    name : NonEmptyString
    
    venue : Ref[Venue]
    
    date : DateTime
    
    artists : List[record ArtistRole {
         artist : Ref[Artist]
         role : String
    }]
}

record Track {
    song : Ref[Song]
    streamingUrls : List[URL]
}

record Album {
    #include EntityBase
    
    title : String
    event : Ref[Event]
    tracks : List[Track]
}

// A Playlist is a collection of entries - these could be albums or solo tracks
record Playlist {
	#include EntityBase
    
	// Name of the playlist, eg "Kids Lullabies"
    name : NonEmptyString
    
    // Who this playlist belongs to
    owner : UserRef

    entries : List[union PlaylistEntry {
    	album : Ref[Album]
        track : Ref[Track]
    }]
}
```

**TODO**: Should we allow inner type definitions?  eg PlaylistEntry or LikeType above.  If so should their fully qualified name be their own name or `<Parent>.name`?

### Schemas features

In the above notice we dont know what is an entity, or what is a relationship.  We are modelling in a way we (the modeller sees fit).   Coincidentally the above looks "like" an ER model.   

Couple more of interesting choices:

* Optionality is interesting since it only denotes the lack of a field value (whether it is a Reference or a Value).   Also Optionality **("?")** can be considered just shorthand for the type `Optional [T]`.
* Default values are not present above since the concept of a default is a serving or a storage artifact and even their semantic highly depandant on the systems that work with this data so they can be provided as annotations when required.

### Limitations

It is obvious that while the core data model for an application/system is easy to represent, its flow through the system is missing and is where a lot of the complexity creeps in.  How we model data ideally is almost always different from how other parts of the system consume this (or some parts of this) data.   Some things that complicate matters are:

* What kind of serving framework are we using - restful?, rpc?
* What kind of transport mechanism?  xml/json/bson?  over Http?, websockets?, custom tcp?
* What storage and indexing platforms re we using and how does data get to those?   
* What transformations are required beyond the online world?
   * Ie for Kafka events,
   * Handling these nearline
   * In the offline world (no union support etc)



## Onering Derivations

What we need is a way to describe derivations of a type into another type that can generate or reason about functions that enable this transformation.   Derivations in Onering aim to solve a part of this problem.  Onering is *not* a language for arbitrary and general purpose computation.   It is instead a tool for declaring data models/schemas and derivations so that specific processors can generate the artifacts they need to hook a new platform (language and/or framework) to work with and add value to the data model.

### Rationale

We had earlier described the model of our data in the application's universe.   Without it being stored it is useless.  Where do we store it?  There are plenty of choices, Relational, Document, No-SQl, Graph and so on.   Each system comes with its own schema DSL/spec to declare structure and constraints.

As an example considering storing our models into a relational DB.   A table description of the user model (in pseudo-SQL) would look like:

```
CREATE TABLE users (
    id varchar(32),
    name varchar(255) NOT NULL,
    createdAt datetime DEFAULT   CURRENT_TIMESTAMP,	
    updatedAt datetime ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
)
```

or if a more typed view is preferred, something like:

```
@sql.table(name = "users")
record User {
	@sql.primarykey
    id : String
    
    @sql.constraint(blank = False, null = False, maxlength = 255)
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

The Address cannot be persisted and has to be used in an embedded way.

Constraints can also be introduced onto the fields.  Annotations help indicate to the toolchain that is consuming this (SQL/ORM) as to what validation to apply and when.

```
record EntityBase {
	@sql.primarykey
    id : String
    
    @sql.constraints(null = False)
    creator : UserRef
    
    @sql.default(auto_now = True)
    createdAt : DateTime
    
    @sql.default(auto_now = True)
    updatedAt : DateTime
}

@sql.table(name = "instruments")
record Instrument : EntityBase {
    @sql.constraints(null = False, blank = False)
    name : String
    
    @sql.constraints(maxlength = 512)
    description : String
    
    @sql.null(True)
    url : URL
}
```

At somepoint relations are required.  For example with the `Artist`:

```
record Artist : EntityBase {
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

The above helps us model "target" schemas easily.   However this has the disadvantage that the linkage between a vanilla Artist and the SQL Artist are not obvious (and are lost).  A backend that converts an Artist retrieved from a SQL backend and converting it to an Artist in the ViewModel is unaware of sameness of the corresponding `name` field.

In order to do over come this, we need something like:

1. Derive a target type while deducing transformation rules.
2. Annotate forward transformation rules to convert source types to a target type.
3. Annotate reverse transformation rules to allow atleast partial conversion back from a derived type to its source types.

**TODO**: Can there be fields in a target type that do *not* exist anywhere in the sources?   

For now the goal of this is to *not* dictate a syntax on what this looks like.  Instead we expect some basic constructs (similar to an expression language) in a derivation, similar to:

```
record Derivation {
    targetName : String
	sourceTypes : List[Type]
    forwardRules : List[DerivationRule]
    reverseRules : List[DerivationRule]
    
    @readonly
    targetType : Type
    
    @readonly
    forwardTransformer : sourceTypes -> targetType
    
    @readonly
    reverseTransformer : targetType -> sourceTypes
}

target DerivationRule {
    targets : List[Location]
    expression : Expression
}

record Location {
    source : Variable
    fieldPath : List[String]
}

record Variable {
    name : String
    type : Type
}

union Expression {
    location : Location
    literal : LiteralValue
    function : FunctionCall
}

record FunctionCall {
    funcName : String
    typeArgs : List[Type]
    arguments : List[Expression]
}
```

Somethings the syntax would consider are:
1. Field renaming/retyping
2. Multiple source types (and source fields)
3. Temp vars/bindings
4. Forward and Reverse rules
5. Non record/Native source types
6. Functions to enable functor behaviors
7. Expressions for data constructors

Note that SQL, GraphQL, Pig all can be transpiled into this intermediate representation for standardization.

**ASSUME** - A way to declare derivations and auto generate transformations exists so we can go from `(X,Y,Z) <-> (A,B,C)`.

### Platform Processors

Our derivation constructs help us pack a lot of the intent!  Now that we have a way to declare master schemas as well as derivations, we need to actually use them.  For this application again, we have something like:

On reads:

1. Client has a page/screen that shows parts of data from our data model.  This is via a [ViewModel](https://msdn.microsoft.com/en-us/magazine/dd419663.aspx) (which is a derivation of the master data model).
2. Client fills this page by making a view request to some endpoint (most likely over Http).
3. The http/app server processes this request and routes this request to multiple resource requests by whoever can serve it.  This assumes auth and request validation has happened.
4. Resource handlers will in turn fetch the resource derivation from their data store.  
5. This resource now needs to be converted into the master data model so it is consumed.
6. However the view model has other transformations it could impose (eg default values, template application, formatting, truncations etc).  This would happen via the transformations generated by the derivations on this side.
7. (6) could either happen before being sent down the wire or after being received by the wire - diff between SSR and SPA?

On the write side:

1. Clients still maintain ViewModels (still derivations of the master data model).   Client converts actions on views as writes to the view model and these are converted into Patch objects on this view model.
2. Inside the network, the patch on a view model is converted into patch on one or more data models.
3. The patches could be to the same resource or multiple resources.  Transactionality needs to be managed here (if possible).
4. resource handlers take this patch on the data model and conver those into patches into the data store model ... and `.save()`.
5. Response returns the success/failure.
6. DataStore model may result in EventModels (say kafka events for different notifications) which are derivations *from* DataStore models.

Does this mean we we need modelling of "requests" and "responses"?  ie RequestModel and ResponseModel.

## Reference Implementation

### Frontend/Client side

Consider an iOS app that displays a list of albums currently in the system.

A view for this would be in the form of a table view that is backed by a data source.  This data source is a derivation of our data model and could be something as simple as:

```
AlbumListSource = GET /albums
AlbumListSource :: List[Album]
```

* This is only a GET call since this is backed by the /albums endpoint.
* There should be a "limit" there but assume server wont return everything.

From this we want something like this to be generated:

```
// We can expect this class to exist and is part of some "async table view" library/pod etc
class AsyncDataSource[T] : UITableViewDataSource {
    results : List[T]
    
    // bunch of things to manage async calls
    abstract asyncLoad() : Future[List[T]];
    
    def entryAt(row : int) : T { return results[row]; }
    def count() : int { return results.length }
}

// ios app dev writes this
class AlbumListSource : AsyncDataSource[Album] {
    api : AlbumListModel
    asyncLoad() : Future[List[Album]] {
    	return api.fetch()
    }
}

// This bit gets code genned from our derivation spec:
class AlbumListModel {
    fetch() : List[Album] {
        return httpGet("/albums").then(results, {
        	return map(toAlbum, toJson(results.payload))
        })
    }
}
```

So how can the derivation for AlbumListModel be specified?

### API Layer

On the API layer/application mid tier we have something like this:

```
def handleRequest(httprequest):
    # validation request arguments
    # Identify N DB objects that need to be updated
    dbObj1 = extractParamsForType1(httprequest)
    dbObj2 = extractParamsForType2(httprequest)
    ...
    dbObjN = extractParamsForTypeN(httprequest)

	``` This could be transactional if supported ```
	saveToDb(dbObj1, dbObj2, ... dbObjN)
    
    event1 = sendKafkaEventFrom(dbObj1, dbObj2)
    event2 = sendKafkaEventFrom(dbObj2, dbObj5, httpRequest.param10)
    ...
```

Firstly there are a couple of problems with this:

1. Wwe are working on http requests directly and this means not having a clean seperation between transport and application level requests.
2. Even though our intent is simply applying `extractParamsForTypeN` such a function never *just* exists or has to be hand crafted and maintained.
3. A DB Object is a very specific representation of our master data models and as a result we are unable to reason about which bits of our data model we are actually working on.
4. And same for other "domains" too - say Kafka events.

### ETL and Offline

Now data stored to any persistent store is ETLed (say onto HDFS or something else for offline processing).

We now have a very similar case where ETLing is just some handler/job that converts data from on schema type (say Data Store models or Event models) to an HDFS model over avro (this could be the same).

One such of this offline processing could be in generating search indexes.   Search indexes can also be though of as derived data that combines several other sources (primary, derived or tracking events etc).

In general our flows look like:

```
[ UIModel ]
     |
     |		[ As Http Request ]
     |
     V
[ Data Models ]
     |
     |		[ UI2Data via HTTP ]
     |
     V
[ Derived Models ]
     |
     |		[ Data2Offline via null transport ]
     |
     V
[ HDFS/Avro ]
     |
     |		[ Offline2Derived Views ]
     |
     V
[ Indexes ]
     |
     |		[ DerivedViews2IndexStorage ]
     |
     V
```

Here we have the concept of "transport" that is really a way to serialize/transmit a model instance.   By decoupling these out, our processing could work directly on "registerd" models only instead of us worring about custom model types.

For instance the DataStoreModel would be an interface that a specific storage engine would implement instead of us worrying about what those look like.
