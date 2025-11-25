# Task tracker handlers

The idea of the directory is to create single class to operate with any kind of the board.

The 'base_handler' file implements common methods and leave abstract for that which depends on the board related entity.
When, each board type has own implementation, for example, 'site_handler'.
And, finally, the 'handler_factory' is the util to init board handler depending on the board related entity type.

If you want to introduce new kind of board, be sure:
1. It has own handler created
2. This handler implements all abstract methods of the TaskTrackerBaseHandler
3. This handler is added to the factory class