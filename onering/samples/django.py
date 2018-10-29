
from onering.common import errors
from onering.typing.core import *

# Describes all types as required by the django model type system
# Source - https://docs.djangoproject.com/en/2.1/ref/models/fields/
Boolean = NativeType()
Int = NativeType()
Long = NativeType()
String = NativeType()

# We have come a long way.  Types can have annotations and we also have a RefinedType 
# that allows types to be decorated with predicates.  Fields are after all types with
# options/predicates/constraints/metadata on them
# Consier the lowly Field.
# 
# A refined type tells us what constraints/decorators are "present" 
# but it does not actually tell us what *cannot* be there
# For a field we can only have a few options like nullable, blank etc
# but adding a random one should not be possible (say tooltip_text) 
# unless we add it.  
#
# Also how do we instantiate these decorators?  For instance these
# decorators may be parametrized.  eg nullable is a True/False that
# can be validated with a function
# Something like:
#
# @nullable(True)   =>  nullable :: Boolean -> (Int -> Boolean)
#                   =>  nullable(True) :: Int -> Boolean
# a : Int
# 
# With refinedtypes each of predicate should return a Boolean by taking in the value
# So in the above nullable should map to something that returns a function when instantiated
# Can we expect *all* predicates to be this way?
# Also nullable should be defined *somewhere* in the target lang/platform
FieldValidatorType = FunctionType("T").with_inputs("T").returns(Boolean)
FieldType = RefinedType("T").add_multi(
                "null", FunctionType().with_inputs(Boolean).returns(FieldValidatorType),
                "blank", FunctionType().with_inputs(Boolean).returns(FieldValidatorType))

    record Field {
        null : boolean = false
        blank : boolean = false
        choices : array<(string, string)>?
        db_column : string?
        index : boolean = false
        default : Any?
        editable : boolean = True
        error_messages : map<string, string>?
        help_text : string = ""
        primary_key : boolean = false
        unique : boolean = false
        verbose_name : string?
        // Commented out because this can be treated with annotations
        // validators : string?
    }

# What are the goals of these types?
# 

namespace onering.django.types {
    // BUT the above is totally crazy syntax in an annotation.  SOOOOO do this instead:
    union FieldAnnotations {
        null : boolean = false
        blank : boolean = false
        choices : array<(string, string)>?
        db_column : string?
        index : boolean = false
        default : Any?
        editable : boolean = True
        error_messages : map<string, string>?
        help_text : string = ""
        primary_key : boolean = false
        unique : boolean = false
        verbose_name : string?
        // Commented out because this can be treated with annotations
        // validators : string?
    }
    @allowed_annotations(FieldAnnotations)
    atomic Field

    # Or alternatively a Field is just a base class
    record Field {
        null : boolean = false
        blank : boolean = false
        choices : array<(string, string)>?
        db_column : string?
        index : boolean = false
        default : Any?
        editable : boolean = True
        error_messages : map<string, string>?
        help_text : string = ""
        primary_key : boolean = false
        unique : boolean = false
        verbose_name : string?
        // Commented out because this can be treated with annotations
        // validators : string?
    }

    # Or another way is why even think of annotation as something belonging to a type
    # but instead look the other way.  For example if a type is int, depending on the
    # context let the annotation do things with it during writes/reads and let an 
    # annotation declare its purpose! 
    # ie isnull annotation can only be applied on writes where as default_values
    # can apply to a read/write but the value itself (in the data) has no idea.
    # So while each can be an annotation and we just wrap a type with a "Field" 
    # generic or a refined type like:

    Field = NativeType(["T"])

    # Field of type T
    record Field[T] {
        null : boolean = false
        blank : boolean = false
        choices : array<(string, string)>?
        db_column : string?
        index : boolean = false
        default : Optional[T]
        editable : boolean = True
        error_messages : map<string, string>?
        help_text : string = ""
        primary_key : boolean = false
        unique : boolean = false
        verbose_name : string?
        // Commented out because this can be treated with annotations
        // validators : string?
    }

    or

    Field = RefinedType[T]

    So a string field with null and blank validations + db column name (say for a name field) could be:

        name = StringField(null = True, blank = False, db_column = "name")

    With native Type:

        record User {
            name = Field[String"].annotations.add(
                    Annotation("django.null", True),
                    Annotation("django.blank", False),
                    Annotation("django.dbcolumn", "name"))
        }

    With refined type:
        # Here we have a Function object that is a reference to a particular function
        # whose type should match the invocation given here.  eg for isnull we would
        # expect it to be isnull :: T -> T -> Bool
        # or isnull[String] :: T -> Bool
        record User {
            name = RefinedType[String].add_multi(
                        Function("isnull")[String].args(True),
                        Function("isblank")[String].args(False)).annotations.add(
                            Annotation("django.db_column", "name"),
                            Annotation("django.index", False),
                            Annotation("django.default", ""),
                            Annotation("django.editable", False),
                            Annotation("django.help_text", "The name field"),
                            Annotation("django.primary_key", False),
                            Annotation("django.unique", True),
                            Annotation("django.verbose_name", "name"),
                            Annotation("django.validators", [ """ pass a list of function names here """ ])
                        )

            # How about a date field?
            birthday = RefinedType[String].add_multi(
                        Function("isnull")[String].args(True),
                        Function("isblank")[String].args(False)).annotations.add(
                            Annotation("django.auto_now", "False"),
                            Annotation("django.auto_now_add", "True"),
                            Annotation("django.auto_now_add", "True"),
                            Annotation("django.db_column", "name"),
                            Annotation("django.index", False),
                            # Observe this - annotations with function references!!!
                            Annotation("django.default", Function("utcnow")),
                            Annotation("django.editable", False),
                            Annotation("django.help_text", "The name field"),
                            Annotation("django.primary_key", True),
                            Annotation("django.unique", True),
                            Annotation("django.verbose_name", "name"),

                            # Note a list of functions as validators
                            Annotation("django.validators", [ Function("ensure_alive"), Function("ensure_curr_life") ])
                        )
            
            # If we can limit annotations by certain types then we get the benefit of doing more auto-typing!
            # Eg:

            union [T] FieldAnnotation {
                @default(False)
                null : Boolean

                @default(False)
                blank : Boolean

                choices : Array[(string, string)]

                db_column : Optional[String]

                @default(False)
                index : Boolean

                default : Optional[T}

                @default(True)
                editable : Boolean

                error_messages : Map[String, String]

                @default("")
                help_text : string

                @default(False)
                primary_key : Boolean

                @default(False)
                unique : Boolean
                verbose_name : Optional[String]
                validators : Array[T -> Bool]
            }
        }

    record CharField : Field { max_length : int }

    union DateFieldAnnotations : FieldAnnotations[DateTime] {
        @default(False)
        auto_now : Boolean

        @default(False)
        auto_now_add : Boolean

        @default(False)
        unique_for_date : Boolean
    }

    union DateTimeFieldCommonAnnotations : FieldAnnotations[DateTime] {
        @default(False)
        auto_now : Boolean

        @default(False)
        auto_now_add : Boolean

        @default(False)
        unique_for_date : Boolean

        @default(False)
        unique_for_year : Boolean
    }

    union DateField : DateTimeField {
    }

    union DateTimeField : DateTimeField {
    }

    record DecimalField : Field {
        max_digits : int?
        decimal_places : int?
    }

    record DurationField : Field { }

    record EmailField : Field {
        max_length : int?
    }

    record FileField : Field {
        max_length : int?
        upload_to : string?
    }

    record FilePathField : Field {
        max_length : int?
        path: string?
        match: string?
        recursive : boolean = false
    }

    record FloatField : Field { }
    record ImageField : Field {
        upload_to : string?
        height_field : string?
        width_field : string?
    }
    record IntegerField : Field { }
    record GenericIPAddressField : Field {
        protocol : string = "both"
        unpack_ipv4 : boolean = false
    }
    record PositiveIntegerField : Field { }
    record PositiveSmallIntegerField : Field { }
    record SlugField : Field { max_length : int  = 50 }
    record SmallIntegerField : Field { }
    record TextField : Field { }
    record TimeField : Field {
        auto_now : boolean = false
        auto_now_add : boolean = false
    }
    record URLField : Field { max_length : int = 200 }
    record UUIDField : Field { }

    record <T> ForeignKey : Field {
        to : T
        on_delete : enum {
            CASCADE
            PROTECT
            SET_NULL
            SET_DEFAULT
            SET
            DO_NOTHING
        }
        limit_choices_to : map<string, Any>?
        related_name : string?
        related_query_name : string?
        to_field : string?
        db_constraint : string?
        swappable : boolean = false
    }

    record <T> OneToOneField : ForeignKey<T> {
        parent_link : boolean = false
    }

    record <T> ManyToManyField : Field {
        limit_choices_to : map<string, Any>?
        related_name : string?
        related_query_name : string?
        through : string?
        through_fields : array<string>?
        db_table : string?
        db_constraint : string?
        symmetrical : boolean = True
    }
}
