from Products.CMFCore.indexing import getQueue


HAS_INDEXING = True


if HAS_INDEXING:
    from collective.ftw.upgrade.interfaces import IDuringUpgrade
    from collective.ftw.upgrade.progresslogger import ProgressLogger
    from zope.globalrequest import getRequest

    class LoggingQueueProcessor:
        """Queue processor to log collective.indexing progress.

        A queue processor is used whenever a collective.indexing queue is
        processed, i.e. when collective.indexing indexes, reindexes or
        unindexes objects in the queue. This may happen several times while
        executing upgrades (e.g. every time when executing a catalog-query).

        For larger deployments with a lot of objects that process may take a
        while, thus we display a progress bar while reindexing.
        """

        should_log = False

        def begin(self):
            self.should_log = IDuringUpgrade.providedBy(getRequest())
            if not self.should_log:
                return

            indexing_queue_length = getQueue().length()
            self.logger = ProgressLogger(
                "Processing indexing queue", indexing_queue_length
            )

        def commit(self):
            pass

        def abort(self):
            pass

        def index(self, obj, attributes):
            if not self.should_log:
                return
            self.logger()

        def reindex(self, obj, attributes, update_metadata=False):
            if not self.should_log:
                return
            self.logger()

        def unindex(self, obj):
            if not self.should_log:
                return
            self.logger()
