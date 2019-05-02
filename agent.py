from pythonian import *
import logging
import time
logger = logging.getLogger('KioAgent')


class KioAgent(Pythonian):
    name = "Kio"  # This is the name of the agent to register with

    def __init__(self, **kwargs):
        super(KioAgent, self).__init__(**kwargs)
        # self.add_ask('test_junk_mail', self.test_junk_mail,
        #              '(test_junk_mail ?x)', True)
        # self.add_ask('test_course_term', self.query_course_terms,
        #              '(courseTerm ?course ?quarter)')
        self.add_ask('courseTerm', self.courseTerm, '(courseTerm ?course ?term)', True)

    def courseTerm(self, courses,terms):
        print(courses)
        print(terms)
        return

    # def test_junk_mail(self, data):
    #     logger.debug(
    #         'testing inserting data into Companion with data: ' + str(data))
    #     return "Send a million dollars to this address"

    def checkCourseTerms(self, data):
        logger.debug('Querying Course Terms')
        self.update_query('(courseTerm ?data)', data)

    def query_course_terms(self):
        logger.debug('Querying Course Terms')
        # self.receive_ask_one('(courseTerm ?course ?term)', [])

if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    a = KioAgent(host='localhost', port=9000, localPort=8951, debug=True)
    # a.test_insert_to_Companion('(started TestAgent)')
    time.sleep(5)
    a.checkCourseTerms('(WinterQuarterFn (AcademicYearFn NorthwesternUniversity (YearFn 2018)))')
