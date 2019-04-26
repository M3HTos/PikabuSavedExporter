from scrapper import Scrapper
import argparse


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--stealth',
        action="store_true",
        dest="stealth",
        help='Фоновый режим'
    )
    parser.add_argument(
        '--save_images',
        action="store_true",
        dest='save_images',
        help='Сохранять ли графику(картинки и гифки)'
    )
    parser.add_argument(
        '-browser',
        dest='browser',
        help='Браузер: Mozilla, Chrome или Opera'
    )
    args = parser.parse_args()
    scrap = Scrapper(driver_type=args.browser,
                     args={
                        "images": args.save_images, "stealth": args.stealth
                     }
    )
    scrap.start()
