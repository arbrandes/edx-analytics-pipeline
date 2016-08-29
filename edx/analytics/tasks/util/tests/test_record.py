"""Test the typed record utilities"""

import datetime
import pickle

from ddt import data, ddt, unpack

from edx.analytics.tasks.tests import unittest
from edx.analytics.tasks.util.record import (
    Record, StringField, IntegerField, DateField, DateTimeField, FloatField, DelimitedStringField, BooleanField,
    DEFAULT_NULL_VALUE,
)

UNICODE_STRING = u'\u0669(\u0361\u0e4f\u032f\u0361\u0e4f)\u06f6'
UTF8_BYTE_STRING = UNICODE_STRING.encode('utf8')


@ddt
class RecordTestCase(unittest.TestCase):
    """Test core record behavior"""

    def test_single_field_pos_arg(self):
        test_record = SingleFieldRecord('foo')
        self.assertEqual(test_record.name, 'foo')

    def test_too_many_pos_args(self):
        with self.assertRaisesRegexp(TypeError, "Too many positional arguments. Unused args: 'bar'"):
            SingleFieldRecord('foo', 'bar')

    def test_not_enough_pos_args(self):
        with self.assertRaisesRegexp(TypeError, "Required fields not specified: name"):
            SingleFieldRecord()

    def test_incorrect_type(self):
        with self.assertRaisesRegexp(
                ValueError, "Unable to assign the value 4 to the field named \"name\": The value is not a string"
        ):
            SingleFieldRecord(4)

    def test_none_arg(self):
        test_record = SingleFieldRecord(None)
        self.assertEqual(test_record.name, None)

    def test_empty_string_arg(self):
        test_record = SingleFieldRecord('')
        self.assertEqual(test_record.name, '')

    def test_field_order(self):
        test_record = TwoFieldRecord('foo', 'bar')
        self.assertEqual(test_record.name, 'foo')
        self.assertEqual(test_record.value, 'bar')

    def test_class_with_other_vars(self):
        class WithOthers(Record):
            """A record with class-level non-Field variables defined."""
            foo = 'foo'
            name = StringField()
            bar = 10

        test_record = WithOthers('baz')

        self.assertEqual(test_record.foo, 'foo')
        self.assertEqual(test_record.name, 'baz')
        self.assertEqual(test_record.bar, 10)

    def test_record_with_no_fields(self):
        test_record = NoFields()

        self.assertEqual(test_record.to_string_tuple(), tuple())
        self.assertItemsEqual(test_record.get_hive_schema(), [])
        self.assertItemsEqual(test_record.get_sql_schema(), [])

    def test_repr_round_trip(self):
        test_record = SampleStruct('foo', 0, datetime.date(2015, 11, 1))
        self.assertEqual(test_record, eval(repr(test_record)))

    def test_initialize_with_kwargs(self):
        test_record = TwoFieldRecord(value='bar', name='foo')
        self.assertEqual(test_record.name, 'foo')
        self.assertEqual(test_record.value, 'bar')

    def test_missing_field_kwargs(self):
        with self.assertRaisesRegexp(TypeError, "Required fields not specified: name"):
            TwoFieldRecord(value='bar')

    def test_mixed_args_kwargs(self):
        test_record = ThreeFieldRecord('a', 'b', third='c')
        self.assertEqual(test_record.first, 'a')
        self.assertEqual(test_record.second, 'b')
        self.assertEqual(test_record.third, 'c')

    def test_mixed_with_missing(self):
        with self.assertRaisesRegexp(TypeError, "Required fields not specified: third"):
            ThreeFieldRecord('a', second='b')

    def test_extra_kwargs(self):
        with self.assertRaisesRegexp(TypeError, "Unknown fields specified: second"):
            SingleFieldRecord('a', second='b')

    def test_mixed_same_arg_appears_twice(self):
        with self.assertRaisesRegexp(
                TypeError, "Multiple values provided for the same field \"name\": 'a' and 'c'"
        ):
            TwoFieldRecord('a', 'b', name='c')

    def test_to_string_tuple(self):
        test_record = SampleStruct(UNICODE_STRING, 0, datetime.date(2015, 11, 1))
        self.assertEqual(
            test_record.to_string_tuple(),
            (UTF8_BYTE_STRING, '0', '2015-11-01')
        )

    def test_to_string_tuple_nulls(self):
        test_record = SampleStruct(None, 0, None)
        self.assertEqual(
            test_record.to_string_tuple(),
            ('\\N', '0', '\\N')
        )

    def test_to_string_tuple_custom_nulls(self):
        test_record = SampleStruct(None, 0, None)
        self.assertEqual(
            test_record.to_string_tuple(null_value='empty'),
            ('empty', '0', 'empty')
        )

    def test_from_string_tuple(self):
        string_tuple = (UTF8_BYTE_STRING, '0', '2015-11-01')
        test_record = SampleStruct.from_string_tuple(string_tuple)
        self.assertEqual(test_record.name, UNICODE_STRING)
        self.assertEqual(test_record.index, 0)
        self.assertEqual(test_record.date, datetime.date(2015, 11, 1))

    def test_from_string_tuple_nulls(self):
        string_tuple = ('\\N', '0', '2015-11-01')
        test_record = SampleStruct.from_string_tuple(string_tuple)
        self.assertEqual(test_record.name, None)
        self.assertEqual(test_record.index, 0)
        self.assertEqual(test_record.date, datetime.date(2015, 11, 1))

    def test_from_string_tuple_custom_nulls(self):
        string_tuple = ('empty', '0', '2015-11-01')
        test_record = SampleStruct.from_string_tuple(string_tuple, null_value='empty')
        self.assertEqual(test_record.name, None)
        self.assertEqual(test_record.index, 0)
        self.assertEqual(test_record.date, datetime.date(2015, 11, 1))

    @data(
        ('foo', '0'),
        ('foo', '0', '2015-11-01', '10')
    )
    def test_from_string_tuple_length_mismatch(self, string_tuple):
        with self.assertRaisesRegexp(
                ValueError, 'The length of the tuple of strings must exactly match the number of fields in the Record'
        ):
            SampleStruct.from_string_tuple(string_tuple)

    @data(
        ('foo', '0', 'foo'),
        ('foo', 'bar', '2015-11-01')
    )
    def test_from_string_tuple_type_mismatch(self, string_tuple):
        with self.assertRaises(ValueError):
            SampleStruct.from_string_tuple(string_tuple)

    def test_sql_schema(self):
        self.assertEqual(
            SampleStruct.get_sql_schema(),
            [
                ('name', 'VARCHAR'),
                ('index', 'INT'),
                ('date', 'DATE')
            ]
        )

    def test_hive_schema(self):
        self.assertEqual(
            SampleStruct.get_hive_schema(),
            [
                ('name', 'STRING'),
                ('index', 'INT'),
                ('date', 'STRING')
            ]
        )

    def test_elasticsearch_properties(self):
        self.assertEqual(
            SampleElasticSearchStruct.get_elasticsearch_properties(),
            {
                'name': {
                    'type': 'string',
                    'index': 'not_analyzed',
                },
                'index': {
                    'type': 'integer',
                },
                'date': {
                    'type': 'date',
                    'index': 'not_analyzed',
                },
                'dateTime': {
                    'type': 'date',
                    'index': 'not_analyzed',
                    'format': 'strict_date_time_no_millis',
                },
            }
        )

    def test_from_tsv_nulls(self):
        tsv_string = '\\N\t0\t2015-11-01\r\n'
        test_record = SampleStruct.from_tsv(tsv_string)
        self.assertEqual(test_record.name, None)
        self.assertEqual(test_record.index, 0)
        self.assertEqual(test_record.date, datetime.date(2015, 11, 1))

    def test_immutability_set(self):
        test_record = SingleFieldRecord(name='foo')
        with self.assertRaisesRegexp(TypeError, 'Records are intended to be immutable'):
            test_record.name = 'bar'

    def test_immutability_set_new_attr(self):
        test_record = SingleFieldRecord(name='foo')
        with self.assertRaisesRegexp(TypeError, 'Records are intended to be immutable'):
            test_record.other = 'bar'

    def test_immutability_del(self):
        test_record = SingleFieldRecord(name='foo')
        with self.assertRaisesRegexp(TypeError, 'Records are intended to be immutable'):
            del test_record.name

    def test_record_debug_str(self):
        test_record = SampleStruct('foo', 0, datetime.date(2015, 11, 1))
        self.assertEqual(str(test_record), "SampleStruct(name='foo', index=0, date=datetime.date(2015, 11, 1))")
        self.assertEqual(str(test_record), repr(test_record))
        self.assertEqual(str(test_record), unicode(test_record))

    def test_equality(self):
        left_record = SingleFieldRecord('a')
        right_record = SingleFieldRecord('a')

        # they should be two references to distinct objects
        self.assertFalse(left_record is right_record)

        self.assertEqual(left_record, right_record)
        self.assertEqual(right_record, left_record)

    def test_not_equality(self):
        left_record = SingleFieldRecord('a')
        right_record = SingleFieldRecord('b')

        self.assertNotEqual(left_record, right_record)
        self.assertNotEqual(right_record, left_record)

    def test_not_equality_different_field_name(self):
        class DifferentFieldName(Record):
            """A record with exactly the same fields as SingleFieldRecord but with a differently named field"""
            last_name = StringField()

        self.assertNotEqual(SingleFieldRecord('a'), DifferentFieldName('a'))

    def test_equality_different_field_constraints(self):
        class DifferentFieldConstraint(Record):
            """A record with exactly the same fields as SingleFieldRecord but with a differently constrained field"""
            name = StringField(nullable=False)

        self.assertEqual(SingleFieldRecord('a'), DifferentFieldConstraint('a'))

    def test_equality_other_class_vars(self):
        class DifferentVars(Record):
            """A record with exactly the same fields as SingleFieldRecord but with different class scoped vars"""
            name = StringField()
            A_CONSTANT = 'foo'  # This will be ignored for equality comparison purposes!

        self.assertEqual(SingleFieldRecord('a'), DifferentVars('a'))

    def test_not_equality_different_field_type(self):
        class DifferentFieldType(Record):
            """A record with exactly the same fields as SingleFieldRecord but with a differently typed field"""
            name = IntegerField()

        self.assertNotEqual(SingleFieldRecord('a'), DifferentFieldType(0))

    def test_not_equality_different_field_order(self):
        class DifferentFieldOrder(Record):
            """A record with exactly the same fields as TwoFieldRecord but with a different field order"""
            value = StringField()
            name = StringField()

        self.assertNotEqual(TwoFieldRecord(name='a', value='b'), DifferentFieldOrder(name='a', value='b'))
        self.assertNotEqual(TwoFieldRecord(name='a', value='b'), DifferentFieldOrder(name='b', value='a'))

    def test_hash(self):
        self.assertEqual(hash(SingleFieldRecord('foo')), hash(SingleFieldRecord('foo')))
        self.assertNotEqual(hash(SingleFieldRecord('foo')), hash(SingleFieldRecord('bar')))

    def test_subclass(self):
        test_record = ExtendedSingleField('a', 'b')
        self.assertEqual(test_record.name, 'a')
        self.assertEqual(test_record.another_field, 'b')

    def test_subclass_non_equality(self):
        left_record = SingleFieldRecord('a')
        right_record = ExtendedSingleField('a', 'b')

        self.assertNotEqual(left_record, right_record)

    def test_subclass_same_fields_equality(self):
        class SingleFieldRecordChild(SingleFieldRecord):
            """A record that extends SingleFieldRecord but doesn't add any fields"""
            pass

        left_record = SingleFieldRecord('a')
        right_record = SingleFieldRecordChild('a')

        self.assertEqual(hash(left_record), hash(right_record))
        self.assertEqual(left_record, right_record)

    def test_similar_records(self):
        class AnotherSingleField(Record):
            """A record with exactly the same fields as SingleFieldRecord but derived directly from Record"""
            name = StringField()

        left_record = AnotherSingleField('foo')
        right_record = SingleFieldRecord('foo')

        self.assertEqual(hash(left_record), hash(right_record))
        self.assertEqual(left_record, right_record)

    def test_set(self):
        arbitrary_set = set()
        arbitrary_set.add(SingleFieldRecord('foo'))
        arbitrary_set.add(SingleFieldRecord('foo'))

        self.assertEqual(len(arbitrary_set), 1)

    def test_dict(self):
        some_dict = {
            SingleFieldRecord('foo'): 1
        }
        some_dict[SingleFieldRecord('foo')] = 2
        self.assertEqual(some_dict[SingleFieldRecord('foo')], 2)

    def test_pickle(self):
        test_record = SampleStruct('a', 10, datetime.date(2015, 11, 1))

        self.assertEqual(pickle.loads(pickle.dumps(test_record)), test_record)

    def test_to_tsv(self):
        test_record = SampleStruct('a', 10, datetime.date(2015, 11, 1))

        self.assertEqual(test_record.to_separated_values(), 'a\t10\t2015-11-01')

    def test_replace(self):
        test_record = SampleStruct('a', 10, datetime.date(2015, 11, 1))
        new_record = test_record.replace(name='b')

        self.assertFalse(test_record is new_record)
        self.assertTrue(new_record.name, 'b')
        self.assertEqual(test_record.index, 10)
        self.assertEqual(test_record.date, datetime.date(2015, 11, 1))

    def test_replace_unknown_field(self):
        test_record = SampleStruct('a', 10, datetime.date(2015, 11, 1))
        with self.assertRaisesRegexp(TypeError, 'Unknown fields specified: foo'):
            test_record.replace(foo='bar')

    def test_replace_empty(self):
        test_record = SampleStruct('a', 10, datetime.date(2015, 11, 1))
        new_record = test_record.replace()

        self.assertFalse(test_record is new_record)
        self.assertEqual(test_record, new_record)

class NoFields(Record):
    """A record without any fields"""
    pass


class SingleFieldRecord(Record):
    """A record with a single string field"""
    name = StringField()


class ExtendedSingleField(SingleFieldRecord):
    """A trivial subclass of a record"""
    another_field = StringField()


class TwoFieldRecord(Record):
    """A record with multiple fields"""
    name = StringField()
    value = StringField()


class ThreeFieldRecord(Record):
    """A record with several fields"""
    first = StringField()
    second = StringField()
    third = StringField()


class SampleStruct(Record):
    """A record with a variety of field types"""
    name = StringField()
    index = IntegerField()
    date = DateField()


class SampleElasticSearchStruct(Record):
    """A record with a variety of field types to illustrate all elasticsearch properties"""
    name = StringField()
    index = IntegerField(analyzed=True)
    date = DateField()
    dateTime = DateTimeField()


@ddt
class StringFieldTest(unittest.TestCase):
    """Tests for StringField"""

    @data(
        'foo',
        u'foo',
        None,
        ''
    )
    def test_validate_success(self, value):
        test_record = StringField()
        self.assertEqual(len(test_record.validate(value)), 0)

    @data(
        10,
        1.0,
        object(),
        False
    )
    def test_validate_error(self, value):
        test_record = StringField()
        self.assertEqual(len(test_record.validate(value)), 1)

    def test_non_nullable(self):
        test_record = StringField(nullable=False)
        self.assertEqual(len(test_record.validate(None)), 1)

    @data(
        '',
        'a',
        'bc',
        'def'
    )
    def test_length_ok(self, value):
        test_record = StringField(length=3)
        self.assertEqual(len(test_record.validate(value)), 0)

    @data(
        'abcd',
        'abcde'
    )
    def test_length_exceeded(self, value):
        test_record = StringField(length=3)
        self.assertEqual(len(test_record.validate(value)), 1)

    def test_sql_type(self):
        test_record = StringField()
        self.assertEqual(test_record.sql_type, 'VARCHAR')

    def test_sql_type_not_null(self):
        test_record = StringField(nullable=False)
        self.assertEqual(test_record.sql_type, 'VARCHAR NOT NULL')

    def test_sql_type_with_length(self):
        test_record = StringField(length=10)
        self.assertEqual(test_record.sql_type, 'VARCHAR(10)')

    def test_length_zero(self):
        with self.assertRaises(ValueError):
            StringField(length=0)

    def test_sql_type_with_length_not_null(self):
        test_record = StringField(length=10, nullable=False)
        self.assertEqual(test_record.sql_type, 'VARCHAR(10) NOT NULL')

    def test_hive_type(self):
        self.assertEqual(StringField().hive_type, 'STRING')


@ddt
class DelimitedStringFieldTest(unittest.TestCase):
    """Tests for DelimitedStringField"""

    @data(
        # String values
        ('abc', 'abc'),
        ('', ''),
        # List values
        (['a', 'b', 'c'], 'a\0b\0c'),
        (('a', 'b', 'c'), 'a\0b\0c'),
        ([], ''),
        ((), ''),
        # Null value (nullable=True by default)
        (None, DEFAULT_NULL_VALUE),
    )
    @unpack
    def test_serialize(self, value, expected_value):
        test_record = DelimitedStringField()
        self.assertEquals(test_record.serialize_to_string(value), expected_value)

    @data(
        # String values
        ('abc', ('abc',)),
        ('', ('',)),
        # List value
        ('a\0b\0c', ('a', 'b', 'c')),
        # Null values (nullable=True by default)
        (DEFAULT_NULL_VALUE, None),
    )
    @unpack
    def test_deserialize(self, value, expected_value):
        test_record = DelimitedStringField()
        self.assertEquals(test_record.deserialize_from_string(value), expected_value)

    @data(
        (DEFAULT_NULL_VALUE, True),
        ('None', False),  # None is just string if nullable=False
    )
    @unpack
    def test_serialize_nullable(self, expected_str, nullable):
        test_record = DelimitedStringField(nullable=nullable)
        self.assertEquals(test_record.serialize_to_string(None), expected_str)

    @data(
        (None, True),
        (('\\N',), False),  # '\\N' is just a string if nullable=False
    )
    @unpack
    def test_deserialize_nullable(self, expected_value, nullable):
        test_record = DelimitedStringField(nullable=nullable)
        self.assertEquals(test_record.deserialize_from_string(DEFAULT_NULL_VALUE), expected_value)

    def test_sql_type(self):
        self.assertEqual(DelimitedStringField().sql_type, 'VARCHAR')

    def test_hive_type(self):
        self.assertEqual(DelimitedStringField().hive_type, 'STRING')

    def test_elasticsearch_type(self):
        self.assertEqual(DelimitedStringField().elasticsearch_type, 'string')

    def test_delimiter(self):
        self.assertEqual(DelimitedStringField().delimiter, '\0')


@ddt
class BooleanFieldTest(unittest.TestCase):
    """Tests for BooleanField"""

    @data(
        # True values
        (-1, 'True'),
        (1, 'True'),
        (10, 'True'),
        (True, 'True'),
        ('True', 'True'),
        (u'True', 'True'),
        ('abc', 'True'),
        (['a'], 'True'),
        ({'a': 1}, 'True'),
        ('False', 'True'),
        (u'False', 'True'),
        ('None', 'True'),
        # False values
        (0, 'False'),
        (False, 'False'),
        ('', 'False'),
        ([], 'False'),
        ({}, 'False'),
        # Null value (nullable=True by default)
        (None, DEFAULT_NULL_VALUE),
    )
    @unpack
    def test_serialize(self, value, expected_value):
        # Test with nullable and not
        for test_record in (BooleanField(), BooleanField(nullable=True)):
            self.assertEquals(test_record.serialize_to_string(value), expected_value)

    @data(
        # True values
        ('True', True),
        (u'True', True),
        ('true', True),
        (u'true', True),
        ('random', True),
        (u'random', True),
        (1, True),
        # False values
        ('False', False),
        (u'False', False),
        ('false', False),
        (u'false', False),
        ('', False),
        (u'', False),
        (0, False),
        # Null values (nullable=True by default)
        (DEFAULT_NULL_VALUE, None),
    )
    @unpack
    def test_deserialize(self, value, expected_value):
        for test_record in (BooleanField(), BooleanField(nullable=True)):
            self.assertEquals(test_record.deserialize_from_string(value), expected_value)

    @data(
        (DEFAULT_NULL_VALUE, True),
        ('False', False),  # None is just false if nullable=False
    )
    @unpack
    def test_serialize_none_nullable(self, expected_str, nullable):
        test_record = BooleanField(nullable=nullable)
        self.assertEquals(test_record.serialize_to_string(None), expected_str)

    @data(
        (None, True),
        (True, False),  # '\\N' is just a string if nullable=False
    )
    @unpack
    def test_deserialize_none_nullable(self, expected_value, nullable):
        test_record = BooleanField(nullable=nullable)
        self.assertEquals(test_record.deserialize_from_string(DEFAULT_NULL_VALUE), expected_value)

    def test_sql_type(self):
        self.assertEqual(BooleanField().sql_type, 'BOOLEAN')

    def test_hive_type(self):
        self.assertEqual(BooleanField().hive_type, 'BOOLEAN')

    def test_elasticsearch_type(self):
        self.assertEqual(BooleanField().elasticsearch_type, 'boolean')


@ddt
class IntegerFieldTest(unittest.TestCase):
    """Tests for IntegerField"""

    @data(
        -1,
        10,
        None,
        0
    )
    def test_validate_success(self, value):
        test_record = IntegerField()
        self.assertEqual(len(test_record.validate(value)), 0)

    @data(
        1.0,
        'foo',
        object()
    )
    def test_validate_error(self, value):
        test_record = IntegerField()
        self.assertEqual(len(test_record.validate(value)), 1)

    def test_sql_type(self):
        self.assertEqual(IntegerField().sql_type, 'INT')

    def test_hive_type(self):
        self.assertEqual(IntegerField().hive_type, 'INT')


@ddt
class DateFieldTest(unittest.TestCase):
    """Tests for DateField"""

    @data(
        datetime.date.today(),
        None
    )
    def test_validate_success(self, value):
        test_record = DateField()
        self.assertEqual(len(test_record.validate(value)), 0)

    @data(
        0,
        False,
        1.0,
        '2015-11-01',
        object()
    )
    def test_validate_error(self, value):
        test_record = DateField()
        self.assertEqual(len(test_record.validate(value)), 1)

    def test_sql_type(self):
        self.assertEqual(DateField().sql_type, 'DATE')

    def test_hive_type(self):
        self.assertEqual(DateField().hive_type, 'STRING')

    def test_serialize_to_string(self):
        self.assertEqual(DateField().serialize_to_string(datetime.date(2015, 11, 1)), '2015-11-01')


@ddt
class DateTimeFieldTest(unittest.TestCase):
    """Tests for DateTimeField"""

    @data(
        datetime.datetime.now(),
        datetime.datetime.now().strftime(DateTimeField.string_format),
        '2015-11-01',
        '2015-11-01 10:10',
        None
    )
    def test_validate_success(self, value):
        test_record = DateTimeField()
        self.assertEqual(len(test_record.validate(value)), 0)

    @data(
        0,
        False,
        1.0,
        'abc',
        object()
    )
    def test_validate_error(self, value):
        test_record = DateTimeField()
        self.assertEqual(len(test_record.validate(value)), 1)

    def test_sql_type(self):
        self.assertEqual(DateTimeField().sql_type, 'DATETIME')

    def test_hive_type(self):
        self.assertEqual(DateTimeField().hive_type, 'STRING')

    def test_elasticsearch_type(self):
        self.assertEqual(DateTimeField().elasticsearch_type, 'date')

    def test_elasticsearch_format(self):
        self.assertEqual(DateTimeField().elasticsearch_format, 'strict_date_time_no_millis')

    def test_deserialize_from_string(self):
        self.assertEqual(DateTimeField().deserialize_from_string('2015-11-01T00:00:00.0'),
                         datetime.datetime(2015, 11, 1))

    def test_serialize_to_string(self):
        self.assertEqual(DateTimeField().serialize_to_string(datetime.datetime(2015, 11, 1)),
                         '2015-11-01T00:00:00.000000')


@ddt
class FloatFieldTest(unittest.TestCase):
    """Tests for FloatField"""

    @data(
        1,
        10.0,
        float('inf'),
        None
    )
    def test_validate_success(self, value):
        test_record = FloatField()
        validation_results = test_record.validate(value)
        self.assertEqual(len(validation_results), 0)

    @data(
        'foobar',
        '2015-11-01',
        object()
    )
    def test_validate_error(self, value):
        test_record = FloatField()
        self.assertEqual(len(test_record.validate(value)), 1)

    def test_sql_type(self):
        self.assertEqual(FloatField().sql_type, 'FLOAT')

    def test_hive_type(self):
        self.assertEqual(FloatField().hive_type, 'FLOAT')

    def test_serialize_to_string(self):
        self.assertEqual(FloatField().serialize_to_string(10.05), '10.05')
        self.assertEqual(FloatField().serialize_to_string(float('inf')), 'inf')

    def test_deserialize_from_string(self):
        self.assertEqual(FloatField().deserialize_from_string('10.05'), 10.05)
        self.assertEqual(FloatField().deserialize_from_string('inf'), float('inf'))
