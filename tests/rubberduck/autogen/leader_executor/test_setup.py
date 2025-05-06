import logging

from rubberduck.autogen.leader_executor import Setup


def test_setup():
    # Configure basic logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Create Setup instance with test instance ID
    instance_id = "pydata__xarray-3095"
    setup = Setup(instance_id, logger=logger)

    try:
        # Set up the environment
        setup.setup_environment()

        # Basic assertion to verify container was created
        assert setup.container is not None, "Container should be created"
        logger.info("Test passed: Container created successfully")

    finally:
        # Clean up resources
        setup.cleanup()
        logger.info("Cleanup completed")


if __name__ == "__main__":
    test_setup()
