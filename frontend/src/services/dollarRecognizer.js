/**
 * The $1 Unistroke Recognizer (JavaScript version)
 *
 * Jacob O. Wobbrock, Ph.D.
 * The Information School
 * University of Washington
 *
 * Andrew D. Wilson, Ph.D.
 * Microsoft Research
 *
 * Yang Li, Ph.D.
 * University of Washington
 *
 * The original software is available at:
 * http://depts.washington.edu/aimgroup/proj/dollar/
 *
 * This port is based on the original C# version.
 */

//
// Point class
//
function Point(x, y) {
	this.X = x;
	this.Y = y;
}

//
// Rectangle class
//
function Rectangle(x, y, width, height) {
	this.X = x;
	this.Y = y;
	this.Width = width;
	this.Height = height;
}

//
// Unistroke class: a unistroke is a list of points
//
function Unistroke(name, points) {
	this.Name = name;
	this.Points = Resample(points, NumPoints);
	var radians = IndicativeAngle(this.Points);
	this.Points = RotateBy(this.Points, -radians);
	this.Points = ScaleTo(this.Points, SquareSize);
	this.Points = TranslateTo(this.Points, Origin);
	this.Vector = Vectorize(this.Points); // for Protractor
}

//
// Result class
//
function Result(name, score) {
	this.Name = name;
	this.Score = score;
}

//
// DollarRecognizer class constants
//
const NumUnistrokes = 16;
const NumPoints = 64;
const SquareSize = 250.0;
const Origin = new Point(0, 0);
const Diagonal = Math.sqrt(SquareSize * SquareSize + SquareSize * SquareSize);
const HalfDiagonal = 0.5 * Diagonal;
const AngleRange = Deg2Rad(45.0);
const AnglePrecision = Deg2Rad(2.0);
const Phi = 0.5 * (-1.0 + Math.sqrt(5.0)); // Golden Ratio

//
// DollarRecognizer class
//
export default function DollarRecognizer() {
	this.Unistrokes = new Array();

	this.AddUnistroke = function (name, points) {
		this.Unistrokes[this.Unistrokes.length] = new Unistroke(name, points);
	}

	this.Recognize = function (points, useProtractor) {
		points = Resample(points, NumPoints);
		var radians = IndicativeAngle(points);
		points = RotateBy(points, -radians);
		points = ScaleTo(points, SquareSize);
		points = TranslateTo(points, Origin);
		var vector = Vectorize(points); // for Protractor

		var b = +Infinity;
		var u = -1;
		for (var i = 0; i < this.Unistrokes.length; i++) {
			var d;
			if (useProtractor) {
				d = OptimalCosineDistance(this.Unistrokes[i].Vector, vector);
			} else {
				d = DistanceAtBestAngle(points, this.Unistrokes[i], -AngleRange, +AngleRange, AnglePrecision);
			}
			if (d < b) {
				b = d;
				u = i;
			}
		}
		const normalizedScore = 1.0 - (b / (Math.PI / 2.0));
		return (u == -1) ? new Result("No match.", 0.0) : new Result(this.Unistrokes[u].Name, normalizedScore);
	}
}

//
// Private helper functions from here on down
//
function Resample(points, n) {
	var I = PathLength(points) / (n - 1); // interval length
	var D = 0.0;
	var newpoints = new Array(points[0]);
	for (var i = 1; i < points.length; i++) {
		var d = Distance(points[i - 1], points[i]);
		if ((D + d) >= I) {
			var qx = points[i - 1].X + ((I - D) / d) * (points[i].X - points[i - 1].X);
			var qy = points[i - 1].Y + ((I - D) / d) * (points[i].Y - points[i - 1].Y);
			var q = new Point(qx, qy);
			newpoints[newpoints.length] = q;
			points.splice(i, 0, q);
			D = 0.0;
		} else {
			D += d;
		}
	}
	if (newpoints.length == n - 1) {
		newpoints[newpoints.length] = new Point(points[points.length - 1].X, points[points.length - 1].Y);
	}
	return newpoints;
}

function IndicativeAngle(points) {
	var c = Centroid(points);
	return Math.atan2(c.Y - points[0].Y, c.X - points[0].X);
}

function RotateBy(points, radians) {
	var c = Centroid(points);
	var cos = Math.cos(radians);
	var sin = Math.sin(radians);
	var newpoints = new Array();
	for (var i = 0; i < points.length; i++) {
		var qx = (points[i].X - c.X) * cos - (points[i].Y - c.Y) * sin + c.X
		var qy = (points[i].X - c.X) * sin + (points[i].Y - c.Y) * cos + c.Y;
		newpoints[newpoints.length] = new Point(qx, qy);
	}
	return newpoints;
}

function ScaleTo(points, size) {
	var B = BoundingBox(points);
	var newpoints = new Array();
	var maxDim = Math.max(B.Width, B.Height); // Use a dimensão maior para a escala
	for (var i = 0; i < points.length; i++) {
		var qx = points[i].X * (size / maxDim); // Aplica a mesma proporção em X
		var qy = points[i].Y * (size / maxDim); // e em Y para manter o aspecto
		newpoints[newpoints.length] = new Point(qx, qy);
	}
	return newpoints;
}

function TranslateTo(points, pt) {
	var c = Centroid(points);
	var newpoints = new Array();
	for (var i = 0; i < points.length; i++) {
		var qx = points[i].X + pt.X - c.X;
		var qy = points[i].Y + pt.Y - c.Y;
		newpoints[newpoints.length] = new Point(qx, qy);
	}
	return newpoints;
}

function Vectorize(points) {
	var sum = 0.0;
	var vector = new Array();
	for (var i = 0; i < points.length; i++) {
		vector[vector.length] = points[i].X;
		vector[vector.length] = points[i].Y;
		sum += points[i].X * points[i].X + points[i].Y * points[i].Y;
	}
	var magnitude = Math.sqrt(sum);
	for (var i = 0; i < vector.length; i++) {
		vector[i] /= magnitude;
	}
	return vector;
}

function OptimalCosineDistance(v1, v2) {
	var a = 0.0;
	var b = 0.0;
	for (var i = 0; i < v1.length; i += 2) {
		a += v1[i] * v2[i] + v1[i + 1] * v2[i + 1];
		b += v1[i] * v2[i + 1] - v1[i + 1] * v2[i];
	}
	var angle = Math.atan(b / a);
	return Math.acos(a * Math.cos(angle) + b * Math.sin(angle));
}

function DistanceAtBestAngle(points, T, a, b, threshold) {
	var x1 = Phi * a + (1.0 - Phi) * b;
	var f1 = DistanceAtAngle(points, T, x1);
	var x2 = (1.0 - Phi) * a + Phi * b;
	var f2 = DistanceAtAngle(points, T, x2);
	while (Math.abs(b - a) > threshold) {
		if (f1 < f2) {
			b = x2;
			x2 = x1;
			f2 = f1;
			x1 = Phi * a + (1.0 - Phi) * b;
			f1 = DistanceAtAngle(points, T, x1);
		} else {
			a = x1;
			x1 = x2;
			f1 = f2;
			x2 = (1.0 - Phi) * a + Phi * b;
			f2 = DistanceAtAngle(points, T, x2);
		}
	}
	return Math.min(f1, f2);
}

function DistanceAtAngle(points, T, radians) {
	var newpoints = RotateBy(points, radians);
	return PathDistance(newpoints, T.Points);
}

function Centroid(points) {
	var x = 0.0, y = 0.0;
	for (var i = 0; i < points.length; i++) {
		x += points[i].X;
		y += points[i].Y;
	}
	x /= points.length;
	y /= points.length;
	return new Point(x, y);
}

function BoundingBox(points) {
	var minX = +Infinity, maxX = -Infinity, minY = +Infinity, maxY = -Infinity;
	for (var i = 0; i < points.length; i++) {
		minX = Math.min(minX, points[i].X);
		minY = Math.min(minY, points[i].Y);
		maxX = Math.max(maxX, points[i].X);
		maxY = Math.max(maxY, points[i].Y);
	}
	return new Rectangle(minX, minY, maxX - minX, maxY - minY);
}

function PathDistance(pts1, pts2) {
	var d = 0.0;
	for (var i = 0; i < pts1.length; i++) {
		d += Distance(pts1[i], pts2[i]);
	}
	return d / pts1.length;
}

function PathLength(points) {
	var d = 0.0;
	for (var i = 1; i < points.length; i++) {
		d += Distance(points[i - 1], points[i]);
	}
	return d;
}

function Distance(p1, p2) {
	var dx = p2.X - p1.X;
	var dy = p2.Y - p1.Y;
	return Math.sqrt(dx * dx + dy * dy);
}

function Deg2Rad(d) { return (d * Math.PI / 180.0); } 