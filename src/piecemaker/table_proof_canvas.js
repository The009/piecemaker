/**
 * Table Proof using canvas.
 *
 * Draws all the pieces onto a scaled to fit canvas to show the initial
 * distribution of pieces.  Pieces are not interactive and all load from inlined
 * img tags that data urls.
 * This is my first time working with the canvas API, so I may have made some
 * rookie mistakes.
 */

class TableProofCanvas {
  constructor(piecemakerIndex, spriteLayout, $container, $canvas, $sprite) {
    this.piecemakerIndex = piecemakerIndex;
    this.spriteLayout = spriteLayout;
    this.$container = $container;
    this.$canvas = $canvas;
    this.$sprite = $sprite;
    this.factor;
    this._zoom = 1.0;
    this._offset = [0, 0];
    this.setCanvasDimensions();
    this.ctx = this.$canvas.getContext('2d', {"alpha": false});
    this.pieces = this.piecemakerIndex.piece_properties.map((pieceProperty) => {
      const pc = new Piece(this.ctx, this.factor, this._zoom, this._offset, this.$sprite,
        this.spriteLayout[String(pieceProperty.id)],
        {
          id: pieceProperty.id,
          x: pieceProperty.x,
          y: pieceProperty.y,
          width: pieceProperty.w,
          height: pieceProperty.h,
        });
      return pc;
    });
  }

  get imageWidth() {
    return this.piecemakerIndex.image_width;
  }
  get imageHeight() {
    return this.piecemakerIndex.image_height;
  }
  get tableWidth() {
    return this.piecemakerIndex.table_width;
  }
  get tableHeight() {
    return this.piecemakerIndex.table_height;
  }

  get zoom() {
    return this._zoom;
  }
  set zoom(zoomLevel) {
    // TODO: improve zooming by maintaining the center.
    this._offset[0] = this._offset[0] - ((this.tableWidth * (zoomLevel - this._zoom) * this.factor * 0.5));
    this._offset[1] = this._offset[1] - ((this.tableHeight * (zoomLevel - this._zoom) * this.factor * 0.5));
    this._zoom = zoomLevel;
    this.render();
  }
  get offset() {
    return [
      this._offset[0],
      this._offset[1],
    ];
  }
  set offset(value) {
    this._offset[0] = value[0];
    this._offset[1] = value[1];
    this.render();
  }

  setCanvasDimensions() {
    const rect = this.$container.getBoundingClientRect();
    const scaleX = rect.width / this.tableWidth;
    const scaleY = rect.height / this.tableHeight;
    const scaleToFit = Math.min(scaleX, scaleY);
    this.factor = scaleToFit;
    this.$canvas.width = Math.ceil(this.factor * this.tableWidth);
    this.$canvas.height = Math.ceil(this.factor * this.tableHeight);
  }

  render() {
    this.clear();
    this.setCanvasDimensions();
    const lineWidth = 2;
    this.drawPuzzleOutline(lineWidth, [
      this._offset[0] + (this._zoom * (this.factor * Math.floor((this.tableWidth - this.imageWidth) * 0.5))),
      this._offset[1] + (this._zoom * (this.factor * Math.floor((this.tableHeight - this.imageHeight) * 0.5))),
      this._offset[0] + (this._zoom * (this.factor * (Math.floor((this.tableWidth - this.imageWidth) * 0.5) + this.imageWidth))),
      this._offset[1] + (this._zoom * (this.factor * (Math.floor((this.tableHeight - this.imageHeight) * 0.5) + this.imageHeight)))
    ])
    this.ctx.save();
    this.pieces.forEach((pc) => {
      pc.factor = this.factor;
      pc.zoom = this.zoom;
      pc.offset = this._offset;
      pc.render();
    });
  }

  drawPuzzleOutline(lineWidth, bbox) {
    this.ctx.save();
    this.ctx.fillStyle = 'rgba(255,255,255,0.2)';
    this.ctx.strokeStyle = 'rgba(255,255,255,0.4)';
    this.ctx.lineWidth = lineWidth;
    this.ctx.beginPath();
    this.ctx.moveTo(bbox[0], bbox[1])
    this.ctx.fillRect(bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1])
    this.ctx.strokeRect(bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1]);
    this.ctx.restore();
  }

  clear() {
    this.ctx.clearRect(0,0, this.$canvas.width, this.$canvas.height);
  }
}

class Piece {
  constructor(ctx, factor, zoom, offset, $sprite, bbox, props) {
    this.ctx = ctx;
    this.factor = factor;
    this.zoom = zoom;
    this.offset = offset;
    this.$sprite = $sprite;
    this.id = props.id;
    this.bbox = bbox;
    this.x = props.x;
    this.y = props.y;
    this.width = props.width;
    this.height = props.height;

    // TODO: Use size-100/sprite_with_padding.jpg and cut them out based on the inlined
    // svg clip paths.
    //this.clipPath = document.getElementById(`p-clip_path-${this.id}`);
  }

  render() {
    //if (!this.clipPath) {
    //  throw "clipPath for piece not found";
    //}
    this.ctx.drawImage(
      this.$sprite,
      this.bbox[0],
      this.bbox[1],
      this.bbox[2],
      this.bbox[3],
      this.offset[0] + (this.x * this.factor * this.zoom),
      this.offset[1] + (this.y * this.factor * this.zoom),
      this.width * this.factor * this.zoom,
      this.height * this.factor * this.zoom
    );
  }
}

window.addEventListener('load', (event) => {
  const $canvas = document.getElementById('piecemaker-table');
  const $container = $canvas.parentElement;
  const $sprite = document.getElementById("piecemaker-sprite_without_padding");
  const $zoomInButton = document.getElementById("zoom-in");
  const $zoomOutButton = document.getElementById("zoom-out");

  if (!$canvas || !$container || !$sprite) {
    throw "Couldn't load elements"
  }
  const scale = $canvas.dataset.size;
  const ctx = $canvas.getContext('2d', {"alpha": false});
  let tableProofCanvas;

  const piecemaker_index_req = fetch("index.json").then(response => response.json());
  const sprite_layout_req = fetch(`size-${scale}/sprite_without_padding_layout.json`).then(response => response.json());
  Promise.all([
    piecemaker_index_req,
    sprite_layout_req
  ]).then((values) => {
    const [piecemaker_index, sprite_layout] = values;
    tableProofCanvas = new TableProofCanvas(piecemaker_index, sprite_layout, $container, $canvas, $sprite);
    tableProofCanvas.render();
    window.addEventListener('resize', () => {
      tableProofCanvas.render();
    });
    let zooming = false;
    let panning = false;
    const zoomAmount = 0.05;
    $canvas.addEventListener('wheel', (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (event.ctrlKey) {
        if (!zooming) {
          window.requestAnimationFrame(() => {
            tableProofCanvas.zoom = tableProofCanvas.zoom + (event.deltaY * zoomAmount);
            zooming = false;
          });
          zooming = true;
        }
      } else {
        if (!panning) {
          window.requestAnimationFrame(() => {
            const offset = tableProofCanvas.offset;
            offset[0] = offset[0] + event.deltaX * 5;
            offset[1] = offset[1] + event.deltaY * 5;
            tableProofCanvas.offset = offset;
            panning = false;
          });
          panning = true;
        }
      }
    });
    $zoomInButton.addEventListener('click', (event) => {
      tableProofCanvas.zoom = tableProofCanvas.zoom + 0.25;
    });
    $zoomOutButton.addEventListener('click', (event) => {
      tableProofCanvas.zoom = tableProofCanvas.zoom - 0.25;
    });
    $canvas.addEventListener('mousedown', (event) => {
      const originOffset = tableProofCanvas.offset;
      const mouseOriginX = event.clientX - originOffset[0];
      const mouseOriginY = event.clientY - originOffset[1];
      function mousemoveHandler(event) {
        if (!panning) {
          const mouseDragX = event.clientX - mouseOriginX;
          const mouseDragY = event.clientY - mouseOriginY;
          window.requestAnimationFrame(() => {
            tableProofCanvas.offset = [mouseDragX, mouseDragY];
            panning = false;
          });
          panning = true;
        }
      }
      function mouseupHandler(event) {
        $canvas.removeEventListener('mousemove', mousemoveHandler);
        $canvas.removeEventListener('mouseup', mouseupHandler);
      }
      $canvas.addEventListener('mousemove', mousemoveHandler);
      $canvas.addEventListener('mouseup', mouseupHandler);
    });

  });
});
