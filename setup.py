from setuptools import setup, find_packages

setup(
    name="unrealircd-config-renderer",
    author="Hashbang Inc.",
    url="https://github.com/hashbang/k8s-irc",
    description="Tool that generates unrealircd config snippets based on kubernetes data",
    long_description=open("README.md").read(),
    project_urls={
        "Homepage": "https://github.com/hashbang/k8s-irc",
        "Source": "https://github.com/hashbang/k8s-irc/",
        "Tracker": "https://github.com/hashbang/k8s-irc/issues",
    },
    long_description_content_type="text/markdown",
    setup_requires=["setuptools_scm"],
    use_scm_version=True,
    packages=find_packages(),
    package_data={"unrealircd_config_renderer": ["templates/*"]},
    entry_points={
        "console_scripts": [
            "unrealircd-config-renderer = unrealircd_config_renderer.cli:main"
        ]
    },
    install_requires=["kubernetes", "jinja2", "requests"],  # needed by kubernetes
    zip_safe=True,
)
