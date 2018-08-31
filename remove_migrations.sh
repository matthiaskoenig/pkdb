
################################
# script to remove migrations
################################
sudo find . -path "*/migrations/*.py" -not -name "__init__.py" -delete && sudo find . -path "*/migrations/*.pyc"
sudo rm -r media/data/
sudo rm -r media/study/
