from __future__ import absolute_import
from __future__ import division
from builtins import str
from builtins import range
from builtins import object
import os
import decimal
import math
from glob import glob
import json
import time

import svgwrite
from PIL import Image
from bs4 import BeautifulSoup
from pixsaw.base import Handler
from glue.managers.simple import SimpleManager

from .paths import interlockingnubs, stochasticnubs
from piecemaker.tools import rasterize_svgfile, potrace, resize_to_max_pixels

variants = {
    interlockingnubs.__name__.replace("piecemaker.paths.", ""),
    stochasticnubs.__name__.replace("piecemaker.paths.", "")
}


class PMHandler(Handler):
    mask_prefix = ""
    piece_prefix = ""


class Pieces(object):
    """
    Creates the piece pngs and pieces info.
    """

    def __init__(self, svgfile, image, mydir, scale=100, max_pixels=0, vector=True):
        " Resize the image if needed. "
        self.vector = vector
        self.mydir = mydir
        self.scale = int(scale)
        # self._image = image
        original_im = Image.open(image)
        im = original_im.copy()
        original_im.close()
        # work on a copy of the image that has been scaled
        (image_root, ext) = os.path.splitext(image)
        self._scaled_image = os.path.join(self.mydir, f"original-{self.scale}{ext}")
        im.save(self._scaled_image)

        if self.scale != 100:
            (w, h) = im.size
            w = int(w * (self.scale / 100.0))
            h = int(h * (self.scale / 100.0))
            im = im.resize((w, h))
            im.save(self._scaled_image)

        (width, height) = im.size
        im.close()

        if max_pixels > 0 and (width * height) > max_pixels:
            (width, height) = resize_to_max_pixels(self._scaled_image, self._scaled_image, max_pixels)

        # scale the svg file
        svgfile_soup = BeautifulSoup(open(svgfile), "xml")
        linessvg = svgfile_soup.svg
        linessvg["width"] = width
        linessvg["height"] = height
        (linessvg_name, ext) = os.path.splitext(os.path.basename(svgfile))
        # scaled_svg is saved at the top level and not inside the scaled
        # directories
        scaled_svg = os.path.join(
            os.path.dirname(svgfile), f"{linessvg_name}-{self.scale}.svg"
        )
        scaled_svg_file = open(scaled_svg, "w")
        # Bit of a hack to work around the lxml parser not handling the default
        # namespace.
        scaled_svg_file.write(str(svgfile_soup.svg).replace("xmlns:=", "xmlns="))
        scaled_svg_file.close()

        # rasterize the svgfile
        scaled_png = rasterize_svgfile(scaled_svg)

        self._mask_dir = os.path.join(self.mydir, "mask")
        os.mkdir(self._mask_dir)
        self._raster_dir = os.path.join(self.mydir, "raster")
        os.mkdir(self._raster_dir)
        self._jpg_dir = os.path.join(self.mydir, "jpg")
        os.mkdir(self._jpg_dir)
        if self.vector:
            self._vector_dir = os.path.join(self.mydir, "vector")
            os.mkdir(self._vector_dir)
        self._pixsaw_handler = PMHandler(
            self.mydir, scaled_png, mask_dir="mask", raster_dir="raster", jpg_dir="jpg"
        )

        self.width = width
        self.height = height

    def cut(self):
        self._pixsaw_handler.process(self._scaled_image)

        if self.vector:
            for piece in glob(os.path.join(self._mask_dir, "*.bmp")):
                potrace(piece, self._vector_dir)

        pieces_json = open(os.path.join(self.mydir, "pieces.json"), "r")
        self.pieces = json.load(pieces_json)

    def generate_resources(self):
        " Create the extra resources to display the pieces. "

        start = time.perf_counter()
        sprite = self._generate_sprite()
        stop = time.perf_counter()
        print(f"_generate_sprite {stop - start}")

        (sprite_width, sprite_height) = sprite.canvas_size
        sprite_layout = {}  # used for showing example layout
        for image in sprite.images:
            filename, ext = image.filename.rsplit(".", 1)
            sprite_layout[int(filename)] = (image.x, image.y)

        if self.vector:
            raster_png = sprite.sprite_path()
            png_sprite = Image.open(raster_png)
            jpg_sprite = png_sprite.convert("RGB")
            png_sprite.close()
            jpg_sprite_file_name = os.path.splitext(raster_png)[0] + ".jpg"
            jpg_sprite.save(jpg_sprite_file_name)
            jpg_sprite.close()
            start = time.perf_counter()
            self._generate_vector(
                sprite_width, sprite_height, sprite_layout, jpg_sprite_file_name
            )
            stop = time.perf_counter()
            print(f"_generate_vector {stop - start}")
            start = time.perf_counter()
            self._sprite_vector_proof(sprite_width, sprite_height, sprite_layout)
            stop = time.perf_counter()
            print(f"_sprite_vector_proof {stop - start}")

        start = time.perf_counter()
        self._sprite_proof(sprite_width, sprite_height, sprite_layout)
        stop = time.perf_counter()
        print(f"_sprite_proof {stop - start}")

    def _sprite_proof(self, sprite_width, sprite_height, sprite_layout):
        """Create a sprite proof showing how the image was cut. Should look like
        original."""
        template = """
<!doctype html>
<html>
<head>
<title>Sprite Proof - {scale}</title>
<link rel="stylesheet" href="raster.css">
<style>
{style}
</style>
</head>
<body>
{pieces}
</body>
</html>"""
        style = """
.pc {
  position: absolute;
  text-indent: -999em;
}
.pc:hover {
  text-indent: 0;
} """
        pieces_html = []
        for (k, v) in self.pieces.items():
            x = v[0]
            y = v[1]
            el = f"""<div class='pc pc--{self.scale} pc-{k}' style='left:{x}px;top:{y}px;'>{k}</div>"""
            pieces_html.append(el)

        pieces = "".join(pieces_html)
        html = template.format(
            **{"scale": self.scale, "pieces": pieces, "style": style}
        )

        f = open(os.path.join(self.mydir, "sprite_proof.html"), "w")
        f.write(html)
        f.close()

    def _sprite_vector_proof(self, sprite_width, sprite_height, sprite_layout):
        """Create a sprite proof showing how the image was cut. Should look like
        original."""
        template = """
<!doctype html>
<html>
<head>
<title>Sprite Vector Proof - {scale}</title>
<link rel="stylesheet" href="raster.css">
<style>
{style}
</style>
</head>
<body>

<svg>
 <defs>
  <image id="source-image-100" xlink:href="raster.jpg"/>

  <clipPath id="piece-mask-100-0" transform="translate(0.000000,220.000000) scale(0.100000,-0.100000)">
    <path d="M54 1988 c-5 -117 -9 -301 -9 -408 0 -167 3 -200 17 -227 39 -71 79 -74 188 -15 56 32 73 36 135 37 120 0 233 -71 271 -171 25 -65 15 -214 -20 -289 -39 -85 -72 -122 -141 -156 -59 -29 -70 -31 -147 -27 -65 3 -96 9 -140 31 -76 36 -112 35 -149 -4 -42 -45 -54 -97 -53 -239 1 -140 40 -458 59 -478 29 -32 873 -52 983 -23 66 17 112 53 112 89 0 14 -11 53 -25 88 -67 167 -70 327 -8 396 102 113 392 71 454 -66 30 -66 24 -102 -29 -158 -17 -19 -26 -42 -29 -75 -4 -42 -1 -53 21 -80 53 -63 149 -85 491 -113 243 -20 429 -43 498 -61 20 -5 42 -7 47 -4 6 4 10 394 10 1086 l0 1079 -1264 0 -1263 0 -9 -212z"/>
  </clipPath>
  <symbol height="220.000000" id="piece-fragment-100-0" viewBox="1258,0,259.000000,220.000000" width="259.000000">
   <use xlink:href="#source-image-100"/>
  </symbol>

</svg>


<svg height="220.000000" id="pc-100-0" width="259.000000">
  <use class="example" clip-path="url(#piece-mask-100-0)" xlink:href="#piece-fragment-100-0"/>
</svg>


{pieces}
</body>
</html>"""
        style = """"""
        pieces_html = []
        # for (k, v) in self.pieces.items():
        #    x = v[0]
        #    y = v[1]
        #    el = f"""<div class='pc pc--{self.scale} pc-{k}' style='left:{x}px;top:{y}px;'>{k}</div>"""
        #    pieces_html.append(el)

        pieces = "".join(pieces_html)
        html = template.format(
            **{"scale": self.scale, "pieces": pieces, "style": style}
        )

        f = open(os.path.join(self.mydir, "sprite_vector_proof.html"), "w")
        f.write(html)
        f.close()

    def _generate_sprite(self):
        " create the css and sprite using glue "
        sprite_manager = SimpleManager(
            source=self._raster_dir,
            css_namespace="pc",
            css_pseudo_class_separator="__",
            css_sprite_namespace="",
            css_url="",
            html=True,
            ratios="1",
            follow_links=False,
            quiet=False,
            recursive=False,
            force=False,
            algorithm="square",
            algorithm_ordering="maxside",
            crop=False,
            padding="0",
            margin="0",
            png8=False,
            retina=False,
            output=self.mydir,
            img_dir=self.mydir,
            css_dir=self.mydir,
            html_dir=self.mydir,
            css_cachebuster=True,
            css_cachebuster_filename=False,
            css_cachebuster_only_sprites=False,
            css_separator="-",
            enabled_formats=["css", "html", "img"],
        )
        sprite_manager.process()

        return sprite_manager.sprites[0]

    def _generate_vector(
        self, sprite_width, sprite_height, sprite_layout, jpg_sprite_file_name
    ):
        " parse the individual piece svg's and create the svg. "

        with open(
            os.path.join(self.mydir, "piece_id_to_mask.json"), "r"
        ) as piece_id_to_mask_json:
            piece_id_to_mask = json.load(piece_id_to_mask_json)
        dwg = svgwrite.Drawing(size=(sprite_width, sprite_height), profile="full")
        dwg.viewbox(width=sprite_width, height=sprite_height)
        dwg.set_desc(title="svg preview", desc="")

        common_path = os.path.commonprefix([self._scaled_image, self.mydir])
        relative_scaled_image = jpg_sprite_file_name[len(common_path) + 1 :]
        source_image = dwg.defs.add(
            dwg.image(
                relative_scaled_image,
                id=f"source-image-{self.scale}",
            )
        )

        for (i, piece_bbox) in self.pieces.items():
            mask_id = piece_id_to_mask[i]
            piece_svg = os.path.join(self._vector_dir, f"{mask_id}.svg")
            preview_offset = sprite_layout[int(i)]

            piece_soup = BeautifulSoup(open(piece_svg), "xml")
            svg = piece_soup.svg
            first_g = svg.g

            clip_path = dwg.defs.add(dwg.clipPath())
            clip_path["id"] = f"piece-mask-{self.scale}-{i}"
            clip_path["transform"] = first_g.get("transform")
            # Later the clip_path gets filled in with the contents

            piece_fragment = dwg.defs.add(dwg.svg())
            piece_fragment["id"] = f"piece-fragment-{self.scale}-{i}"

            vb = svg.get("viewBox")
            # TODO could also be separated by ','?
            (minx, miny, vbwidth, vbheight) = vb.split(" ")
            piece_fragment.viewbox(
                minx=preview_offset[0],
                miny=preview_offset[1],
                width=vbwidth,
                height=vbheight,
            )
            piece_fragment["width"] = vbwidth
            piece_fragment["height"] = vbheight

            use = piece_fragment.add(dwg.use(source_image))

            example_use = dwg.add(
                dwg.use(piece_fragment, clip_path=f"url(#piece-mask-{self.scale}-{i})")
            )
            # layout the svg pieces exactly like glue did.
            example_use["transform"] = "translate( %s, %s )" % (preview_offset)
            example_use["class"] = "example"

        preview_soup = BeautifulSoup(dwg.tostring(), "xml")

        for (i, piece_bbox) in self.pieces.items():
            mask_id = piece_id_to_mask[i]
            piece_svg = os.path.join(self._vector_dir, f"{mask_id}.svg")
            piece_soup = BeautifulSoup(open(piece_svg), "xml")
            svg = piece_soup.svg
            first_g = svg.find("g")
            piece_mask_tag = preview_soup.defs.find(
                "clipPath", id=f"piece-mask-{self.scale}-{i}"
            )
            if piece_mask_tag:
                new_g = first_g.wrap(preview_soup.new_tag("g"))
                first_g.unwrap()  # don't need this g with it's attributes
                piece_mask_tag.append(new_g)
                piece_mask_tag.g.unwrap()  # strip out the g leaving contents

        out = open(os.path.join(self.mydir, "preview.svg"), "w")
        out.write(preview_soup.prettify())
        out.close()


# see adjacent.py


class JigsawPieceClipsSVG(object):
    """
    Renders a svg file of jigsaw puzzle piece paths.
    """

    title = "Jigsaw puzzle piece clips"
    minimum_count_of_pieces = 9
    # TODO: what should the maximum_count_of_pieces be for this?
    maximum_count_of_pieces = 150000

    def __init__(
        self,
        width,
        height,
        pieces=0,
        minimum_piece_size=42,
        variant="interlockingnubs"
    ):

        self.width = width
        self.height = height
        if variant not in variants:
            raise Exception("invalid variant")
        self.HorizontalPath = globals().get(variant).HorizontalPath
        self.VerticalPath = globals().get(variant).VerticalPath
        _pieces = pieces

        if minimum_piece_size > 0:
            # Get the maximum number of pieces that can fit within the
            # dimensions depending on the minimum piece size.
            max_pieces_that_will_fit = int(
                (width / minimum_piece_size)
                * (height / minimum_piece_size)
            )
            if _pieces > 0:
                # Only use the piece count that is smaller to avoid getting too
                # small of pieces.
                _pieces = min(max_pieces_that_will_fit, _pieces)
            else:
                _pieces = max_pieces_that_will_fit

        _pieces = max(_pieces, self.minimum_count_of_pieces)
        _pieces = min(_pieces, self.maximum_count_of_pieces)

        (self._rows, self._cols) = self._gridify(width, height, _pieces)

        # adjust piece count
        _pieces = self._rows * self._cols
        # set piece dimensions
        self._piece_width = float(width) / float(self._cols)
        self._piece_height = float(height) / float(self._rows)

        description = f"Created with the piecemaker. Piece count: {_pieces}"
        # create a drawing
        # Use shape-rendering='optimizeSpeed' to not anti-alias the lines
        self._dwg = svgwrite.Drawing(
            size=(self.width, self.height),
            profile="full",
            **{"shape-rendering": "geometricPrecision"},
        )
        self._dwg.viewbox(width=self.width, height=self.height)
        self._dwg.stretch()
        self._dwg.set_desc(title=self.title, desc=description)

        self._create_lines()

    def _gridify(self, width, height, pieces, add_more_pieces=True):
        """
        Based on area of the box, determine the count of rows and cols that
        will meet the number of pieces.
        """
        area = decimal.Decimal(width * height)
        s = area.sqrt()
        n = decimal.Decimal(pieces).sqrt()
        piece_size = float(s / n)
        # use math.ceil to at least have the target count of pieces
        rounder = math.ceil
        if not add_more_pieces:
            rounder = math.floor
        rows = int(rounder(height / piece_size))
        cols = int(rounder(width / piece_size))
        return (rows, cols)

    def svg(self, filename=None):
        if filename is None:
            return self._dwg.tostring()
        else:
            # TODO: write svg to filename
            pass

    def _create_lines(self):
        # create vertical and horizontal lines on a white background
        self._initial_bg()
        self._vertical_lines()
        self._horizontal_lines()

    def _initial_bg(self):
        layer = self._dwg.add(self._dwg.g())
        g = layer.add(self._dwg.g())
        fullsize_rect = g.add(
            self._dwg.rect(insert=(0, 0), size=(self.width, self.height))
        )
        fullsize_rect["fill"] = "white"

    def _vertical_lines(self):
        layer = self._dwg.add(self._dwg.g())
        for i in range(0, self._cols - 1):  # except last one
            g = layer.add(self._dwg.g())
            start = (i + 1) * self._piece_width
            curvelines = [
                "M 0 0 ",  # origin
                "L %f 0 " % start,
            ]
            for j in range(0, self._rows):
                interlockingnub_path = self.VerticalPath(width=self._piece_height, height=self._piece_width)
                curvelines.append(interlockingnub_path.render())

            curvelines.append("L 0 %i " % self.height)  # end
            curveline = " ".join(curvelines)
            path = g.add(self._dwg.path(curveline))
            path["stroke"] = "black"
            path["stroke-width"] = "1"
            path["style"] = "vector-effect:non-scaling-stroke;"
            # svgo will optimize by moving the style for vector-effect to be an
            # attribute.  path["vector-effect"] = "non-scaling-stroke"
            path["fill"] = "none"

    def _horizontal_lines(self):
        layer = self._dwg.add(self._dwg.g())
        for i in range(0, self._rows - 1):  # except last one
            g = layer.add(self._dwg.g())
            start = (i + 1) * self._piece_height
            curvelines = [
                "M 0 0 ",
                "L 0 %f " % start,
            ]
            for j in range(0, self._cols):
                interlockingnub_path = self.HorizontalPath(width=self._piece_width, height=self._piece_height)
                curvelines.append(interlockingnub_path.render())

            curvelines.append("L %i 0 " % self.width)  # end
            curveline = " ".join(curvelines)
            path = g.add(self._dwg.path(curveline))
            path["stroke"] = "black"
            path["stroke-width"] = "1"
            path["style"] = "vector-effect:non-scaling-stroke;"
            # svgo will optimize by moving the style for vector-effect to be an
            # attribute.  path["vector-effect"] = "non-scaling-stroke"
            path["fill"] = "none"
