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

A way to encode the above rules takes the general form of:

```
(record|union|enum) <NameOfDerivedType> derives SourceTypeSpecs {
	derivation_rule1
    derivation_rule2
    ...
    derivation_ruleN
}

SourceTypeSpecs ::= SourceTypeSpec
				|  SourceTypeSpec "," SourceTypeSpecs
                
SourceTypeSpec ::= "explicit" ? SourceType ("as" varname) ?

derivation_rule ::= field_spec | forward_rule | backward_rule

forward_rule ::= field_spec + "<=" expression
reverse_rule ::= expression "=>" field_spec +

field_spec ::= var1 ( "." var2 )*
```

A target type (record or union) can derive from multiple source types (themselves being unions or records) and define derivation rules that select/project fields from source types into the target type.  This by default copies **all** of the fields from the source types into the target type.

As a simple User derivation is below.  Note the `id` and `name` fields.  They are "derived" as is and their types are inferred by default.

```
namespace org.onering.samples.sql {
    @sql.table(name = "users")
    record User derives org.onering.samples.vanilla.User {
        @sql.primarykey
        id

        @sql.constraint(blank = False, null = False)
        name
    }
}
```

### Renamed and Retyped fields

While in the original data model createdAt and updatedAt were typed as `DataTime`, here these may have to be retyped as Long (or even renamed), this can just be done with a retyping rule:


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
	}
}
```

The conversion between a DateTime (whatever that is) to a Long for `createdAt` will be done automatically by Onering if it finds a suitable converter.  

Sometimes a suitable converter may not be found in which case a converter function can be specified:


```
namespace org.onering.samples.sql {
    @sql.table(name = "users")
    record User derives org.onering.samples.vanilla.User {
		...
        
		// Let Onering find a DataTime to Long transformer
        @sql.default(auto_now = True)
        updatedAt as updatedOn : Long using DateTime2Long
        
        // or specify a custom transformer - note DateTime2Long tells
        // us what the target type will be!
        @sql.default(auto_now = True)
        updatedAt as updatedOn using DateTime2Long
    }
}
```

**Note**: Annotations are still arbitrary and plugged into be used by the target processor.

### Target Type Generation

A derivation has enough information to result in a target User record that is equivalent to the below record without actually typing it up but also maintaining linkages across fields:

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

Additionally we also have functions that can convert from the vanilla User record to the SQL User record with the signature:

```
vanilla.User -> sql.User
```

### Multi source derivations

Sometimes it would make sense to derive a target field from several fields.  Perhaps multiple records into a union.  Or taking parts of multiple unions or simply cherrypicking parts of multiple records into a record.  This can be done with:

```
record SongWithLyrics derives explicit Song as song, explicit Lyrics as lyrics {
    song.title as songTitle
    lyrics.firstSection as sampleSection
}
```

This would result in:

```
record SongWithLyrics {
    songTitle : String
    sampleSection : Section
}
```

Note the "explicit" qualifier in the derivation.  By default "all" fields are derived/included in the target type with the renames being "add-ons".   Sometimes we want to only extract fields by default instead of all.   The "explicit" qualifier *only* introduces new fields and none of the old fields in the particular source.   Within a list of sources, some can be explicit and some can be "all".

### Duplicate source types

Source types can also have duplicate types and this is nothing special.  For instance a Duet could involve the first section of two different song lyrics:

```
record Duet derives explicit Lyrics as vocal, explicit Lyrics as instrument {
    vocal.firstSection as vocalSection
    instrument.firstSection as instrumentSection
}
```

resulting in:

```
record Duet {
    vocalSection : String
    instrumentSection : Section
}
```

### NativeType Sources

Well why not have multiple lyrics instead of just two?

```
record Concerto derives List[Lyrics] as lyrics {
    ???
}
```

List is a native/opaque type.   In Onering lists/maps/arrays are not special by any means.   The easiest way to enable this transformation is via an external function (with type signature `List[Lyrics] -> List[Section]`):

```
record Concerto derives List[Lyrics] as lyrics {
    lyrics as firstSections : List[Section] using ExtractSections[Lyrics, Sections]
}
```

### Composition Style

The above has the disadvantage of having to implemnt a `map` iteration in every external function.  Onering provides `interfaces` that result in better compositional style of declarations.

**ASSUME**: We have a way to define functors (or interfaces).

ie something like:

```
native List[T] enables Functor

or

native List[T] implements Functor
```

so we can do:

```
// Assuming InputList = [1,2,3,4,5]
fmap squareIt InputList

or 

InputList.fmap(squareIt)
```

With traits/protocols/interfaces/typeclasses we can simply do:

```
record Concerto derives List[Lyrics] as lyrics {
    firstSections as fmap(FirstLyricSection, lyrics) as firstSections : List[Section]
}
```

`FirstLyricSection` is a UDF that converts a `Lyrics` instance to a `Section` instance (in this case by simply returning lyrics.firstSection).

This could apply to other parametrized native types too (eg `Map[K,V]`) as long as they provide a functor implementation for given types.


But is this the case of construct chasing syntax?   A derivation is a rule that says 3 things:

1. Here is a target type.
2. Here are the "rules" to create fields in the target type
3. Here are the rules to go "backwards".

Note that (2) must be "complete" in that it does not make sense for there to be any field in the target type that is not already a function of existing fields.  ie we cannot introduce new origin fields in the derived type since that would mean our data model itself is not complete.

(3) however can definitely be "incomplete".   (3) describes the rules to take an instance of a derived type and traverse back to the source type(s).   This is fair since in most cases derived types may just be partial data from the source types.

So our derivations without any fanfare could just be:

```
record X derives A,B,C {
    targetField1, targetField2.... <= F(sf1, sf2, sf3 ....)
    RF(tf1, tf2, tf3 ...) => sourceField1, sourceField2...
}
```

### Validation Errors

In more complex cases multiple validations would need to be applied which may fail or succeed.  While treating this is an all or nothing will work, more sophistiction error handling schemes should be allowed (like say collecting all errors).

Consider the example of extracting an `Address` instance *from* a json object (or even a HttpRequest).

```
record Address derives HttpRequest as hreq {
}
```

### Derivation Schema

A derivation can be typed as follows:

```
Derivation := 
		
```
### Projections
