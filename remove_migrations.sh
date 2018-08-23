################################
# script to remove migrations
################################
sudo find . -path "*/migrations/*.py" -not -name "__init__.py" -delete && sudo find . -path "*/migrations/*.pyc"  -delete
sudo rm -r media/study/
sudo rm -r media/data/
